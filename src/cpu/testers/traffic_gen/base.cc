/*
 * Copyright (c) 2012-2013, 2016-2020 ARM Limited
 * All rights reserved
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
#include "cpu/testers/traffic_gen/base.hh"

#include <sstream>

#include "base/intmath.hh"
#include "base/random.hh"
#include "config/have_protobuf.hh"
#include "cpu/testers/traffic_gen/base_gen.hh"
#include "cpu/testers/traffic_gen/dram_gen.hh"
#include "cpu/testers/traffic_gen/dram_rot_gen.hh"
#include "cpu/testers/traffic_gen/exit_gen.hh"
#include "cpu/testers/traffic_gen/hybrid_gen.hh"
#include "cpu/testers/traffic_gen/idle_gen.hh"
#include "cpu/testers/traffic_gen/linear_gen.hh"
#include "cpu/testers/traffic_gen/nvm_gen.hh"
#include "cpu/testers/traffic_gen/random_gen.hh"
#include "cpu/testers/traffic_gen/stream_gen.hh"
#include "cpu/testers/traffic_gen/strided_gen.hh"
#include "debug/Checkpoint.hh"
#include "debug/TrafficGen.hh"
#include "enums/AddrMap.hh"
#include "params/BaseTrafficGen.hh"
#include "sim/sim_exit.hh"
#include "sim/stats.hh"
#include "sim/system.hh"

#if HAVE_PROTOBUF
#include "cpu/testers/traffic_gen/trace_gen.hh"
#endif

namespace gem5
{

BaseTrafficGen::BaseTrafficGen(const BaseTrafficGenParams &p)
    : ClockedObject(p),
      system(p.system),
      elasticReq(p.elastic_req),
      progressCheck(p.progress_check),
      noProgressEvent([this]{ noProgress(); }, name()),
      nextTransitionTick(0),
      nextPacketTick(0),
      maxOutstandingReqs(p.max_outstanding_reqs),
      port(name() + ".port", *this),
      retryPkt(NULL),
      retryPktTick(0), blockedWaitingResp(false),
      updateEvent([this]{ update(); }, name()),
      stats(this),
      requestorId(system->getRequestorId(this)),
      streamGenerator(StreamGen::create(p)),
      dramBitmask(p.dram_bitmask),
      channelBitmask(p.channel_bitmask),
      pseudoChannelBitmask(p.pseudo_channel_bitmask),
      targetBanks(p.target_banks),
      targetChannels(p.target_channels),
      targetPseudoChannels(p.target_pseudo_channels),
      minPeriod(p.min_period),
      maxPeriod(p.max_period),
      readRatio(p.rd_ratio),
      checkSystemFlagEvent([this]{ checkSystemFlag(); }, name()),
      trafficStarted(false)
      trafficStarted(false),
      targetBandwidth(p.target_bandwidth)
{
}

BaseTrafficGen::~BaseTrafficGen()
{
}

Tick
BaseTrafficGen::calculatePeriodForBandwidth(uint64_t packet_size)
{
    if (targetBandwidth == 0) {
        return minPeriod;
    }

    // Calculate period more conservatively
    double period_in_seconds = (double)packet_size / targetBandwidth;
    Tick calculated_period = (Tick)(period_in_seconds * 1e12);

    // Don't go below minimum period
    calculated_period = std::max(calculated_period, minPeriod);

    return calculated_period;
}

void
BaseTrafficGen::startup()
{
    ClockedObject::startup();

    // Schedule the first check after startup (safe after checkpoint restore)
    if (!trafficStarted) {
        schedule(checkSystemFlagEvent, curTick() + 1000);
    }
}

void
BaseTrafficGen::checkSystemFlag()
{
    // Check if system flag is set and we haven't started yet
    if (system->startTrafficGen && !trafficStarted) {
        trafficStarted = true;
        start();  // Start traffic generation
        DPRINTF(TrafficGen,"Traffic generator started due to system flag\n");
        return;  // Don't reschedule - we're done checking
    }

    // If not started yet, schedule next check
    if (!trafficStarted) {
        schedule(checkSystemFlagEvent, curTick() + 1000);
    }
}

Port &
BaseTrafficGen::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "port") {
        return port;
    } else {
        return ClockedObject::getPort(if_name, idx);
    }
}

void
BaseTrafficGen::init()
{
    ClockedObject::init();

    if (!port.isConnected())
        fatal("The port of %s is not connected!\n", name());
}

DrainState
BaseTrafficGen::drain()
{
    if (!updateEvent.scheduled()) {
        // no event has been scheduled yet (e.g. switched from atomic mode)
        return DrainState::Drained;
    }

    if (retryPkt == NULL) {
        // shut things down
        nextPacketTick = MaxTick;
        nextTransitionTick = MaxTick;
        deschedule(updateEvent);
        return DrainState::Drained;
    } else {
        return DrainState::Draining;
    }
}

void
BaseTrafficGen::serialize(CheckpointOut &cp) const
{
    warn("%s serialization does not keep all traffic generator"
         " internal state\n", name());

    DPRINTF(Checkpoint, "Serializing BaseTrafficGen\n");

    // save ticks of the graph event if it is scheduled
    Tick nextEvent = updateEvent.scheduled() ? updateEvent.when() : 0;

    DPRINTF(TrafficGen, "Saving nextEvent=%llu\n", nextEvent);

    SERIALIZE_SCALAR(nextEvent);

    SERIALIZE_SCALAR(nextTransitionTick);

    SERIALIZE_SCALAR(nextPacketTick);
}

void
BaseTrafficGen::unserialize(CheckpointIn &cp)
{
    warn("%s serialization does not restore all traffic generator"
         " internal state\n", name());

    // restore scheduled events
    Tick nextEvent;
    UNSERIALIZE_SCALAR(nextEvent);
    if (nextEvent != 0)
        schedule(updateEvent, nextEvent);

    UNSERIALIZE_SCALAR(nextTransitionTick);

    UNSERIALIZE_SCALAR(nextPacketTick);
}

unsigned int
BaseTrafficGen::extractAddressBits(unsigned long mask, Addr addr) const
{
    // Port of your C code paddr_to_color() function
    unsigned int color = 0;
    unsigned int idx = 0;

    // Extract bits based on mask (same logic as your C code)
    for (unsigned int bit_pos = 0; bit_pos < 64; bit_pos++) {
        if (mask & (1UL << bit_pos)) {
            if ((addr >> bit_pos) & 0x1) {
                color |= (1 << idx);
            }
            idx++;
        }
    }
    return color;
}

bool
BaseTrafficGen::shouldFilterAddress(Addr addr) const
{
    // Default to true if no filters are specified
    bool bank_match = targetBanks.empty();
    bool channel_match = targetChannels.empty();
    bool pseudo_channel_match = targetPseudoChannels.empty();

    // Check bank match (same as your C code g_color filtering)
    if (!targetBanks.empty()) {
        unsigned int bank = extractAddressBits(dramBitmask, addr);
        for (unsigned int target_bank : targetBanks) {
            if (bank == target_bank) {
                bank_match = true;
                break;
            }
        }
    }

    // Check channel match (same as your C code g_channel filtering)
    if (!targetChannels.empty()) {
        unsigned int channel = extractAddressBits(channelBitmask, addr);
        for (unsigned int target_channel : targetChannels) {
            if (channel == target_channel) {
                channel_match = true;
                break;
            }
        }
    }

    // Check pseudo-channel match (same as your C code g_pseudo_channel
    // filtering)
    if (!targetPseudoChannels.empty()) {
        unsigned int pseudo_channel =
            extractAddressBits(pseudoChannelBitmask, addr);
        for (unsigned int target_pseudo_channel : targetPseudoChannels) {
            if (pseudo_channel == target_pseudo_channel) {
                pseudo_channel_match = true;
                break;
            }
        }
    }

    // Address passes filter if ALL conditions match
    // (same as your C code logic)
    return bank_match && channel_match && pseudo_channel_match;
}

void
BaseTrafficGen::update()
{
    // shift our progress-tracking event forward
    reschedule(noProgressEvent, curTick() + progressCheck, true);

    // if we have reached the time for the next state transition, then
    // perform the transition
    if (curTick() >= nextTransitionTick) {
        transition();
    } else {
        assert(curTick() >= nextPacketTick);

        size_t current_outstanding = waitingResp.size();

        // ADAPTIVE STRATEGY: Allow bursts when system is responsive
        size_t base_limit = maxOutstandingReqs;
        size_t adaptive_limit = base_limit;

        // If we're making good progress (not blocked, no retries), allow more
        if (!blockedWaitingResp && retryPkt == NULL &&
            current_outstanding < (base_limit / 2)) {
            adaptive_limit = base_limit + (base_limit / 2);  // 1.5x normal
            DPRINTF(TrafficGen, "%s: System responsive, allowing burst mode "
                    "(%zu limit)\n", name(), adaptive_limit);
        }

        // But never exceed absolute safety limit
        size_t absolute_max = std::min(adaptive_limit, (size_t)64);

        if (current_outstanding >= absolute_max) {
            // Back off, but not too aggressively if we're just hitting
            // burst limit
            Tick backoff_period = (current_outstanding > base_limit) ?
                                  (minPeriod * clockPeriod()) :     // Short
                                  (maxPeriod * clockPeriod() * 2);  // Longer

            nextPacketTick = curTick() + backoff_period;
            scheduleUpdate();
            return;
        }

        // Continue with normal packet generation...
        // get the next packet and try to send it
        PacketPtr pkt = activeGenerator->getNextPacket();
        if (pkt) {
            pkt->req->setFlags(pkt->req->getFlags() | Request::UNCACHEABLE);
            DPRINTF(TrafficGen, "%s: Generated packet: %s\n",
                name().c_str(), pkt ? "SUCCESS" : "NULL");
        }

        // If generating stream/substream IDs are enabled,
        // try to pick and assign them to the new packet
        if (streamGenerator) {
            auto sid = streamGenerator->pickStreamID();
            auto ssid = streamGenerator->pickSubstreamID();

            pkt->req->setStreamId(sid);

            if (streamGenerator->ssidValid()) {
                pkt->req->setSubstreamId(ssid);
            }
        }

        bool is_memory_addr = pkt && system->isMemAddr(pkt->getAddr());
        bool passes_address_filter = true;
        if (pkt && is_memory_addr) {
            passes_address_filter = shouldFilterAddress(pkt->getAddr());

        }

        if (pkt && is_memory_addr && passes_address_filter) {
            stats.numPackets++;
            // Only attempts to send if not blocked by pending responses
            blockedWaitingResp = allocateWaitingRespSlot(pkt);
            if (blockedWaitingResp || !port.sendTimingReq(pkt)) {
                retryPkt = pkt;
                retryPktTick = curTick();
            }
        } else if (pkt) {
            // Packet filtered out - delete it and continue
            if (!is_memory_addr) {
                ++stats.numSuppressed;
            } else if (!passes_address_filter) {
                ++stats.numSuppressedByFilter;
            }

            ++stats.numSuppressed;
            if (!(static_cast<int>(stats.numSuppressed.value()) % 1000000)) {
                // warn("%s suppressed %d packets\n",
                // name(), stats.numSuppressed.value());
            }

            delete pkt;
            pkt = nullptr;
        }
    }

    // If waiting for retry or response, don't schedule more events.
    // On transition or successful send, schedule next update.
    if (retryPkt == NULL) {
        if (targetBandwidth > 0) {
            // Use calculated period for bandwidth control
            nextPacketTick = curTick() +
                calculatePeriodForBandwidth(64);
        } else {
            // Use original period calculation
            nextPacketTick =
                activeGenerator->nextPacketTick(elasticReq, 0);
        }
        scheduleUpdate();
    }
}

void
BaseTrafficGen::createSimpleGenerator()
{
    std::string gen_name = name();
    int gen_id = 0;
    size_t pos = gen_name.find("traffic_gen");
    if (pos != std::string::npos) {
        std::string id_str = gen_name.substr(pos + 11);
        gen_id = std::stoi(id_str) - 1;
    }

    Tick duration = 20000000000;      // 20 billion ticks
    Addr base_start = 0x200000000;
    Addr base_end = 0x400000000;
    Addr total_size = base_end - base_start;

    Addr addr_space_per_gen = total_size / 10;
    Addr start_addr = base_start + (gen_id * addr_space_per_gen);
    Addr end_addr = start_addr + addr_space_per_gen;

    // BANDWIDTH TRICK 1: Use larger block sizes
    // Same number of packets, but more bytes per packet = higher bandwidth
    Addr block_size = 64;  // 2x larger blocks = 2x bandwidth with same count
    // Or even: Addr block_size = 256;  // 4x larger blocks = 4x bandwidth

    Tick duration = 50000000000;

    // Ensure COMPLETELY separate address ranges
    Addr base_start = 0x200000000;
    Addr base_end   = 0x280000000;
    Addr total_size = base_end - base_start;

    // Divide address space with gaps to avoid cache line conflicts
    Addr space_per_gen = total_size / 4;
    Addr start_addr = base_start + gen_id * space_per_gen * 2;
    Addr end_addr = start_addr + space_per_gen;

    // Ensure cache line alignment (64-byte boundaries)
    start_addr = (start_addr + 63) & ~63ULL;
    end_addr = end_addr & ~63ULL;



    Addr block_size = 64;
    Tick min_period = minPeriod;
    Tick max_period = maxPeriod;
    uint8_t read_percent = readRatio;
    Addr data_limit = 0;

    // BANDWIDTH TRICK 2: Use DRAM generator for burst patterns
    // This generates more efficient memory access patterns
    unsigned int num_seq_pkts = 8;         // 8 sequential packets per burst
    unsigned int page_size = 8192;        // 8KB page size
    unsigned int nbr_of_banks = 16;       // Use all banks for parallelism
    unsigned int nbr_of_banks_util = 16;  // Utilize all banks
    enums::AddrMap addr_mapping = enums::AddrMap::RoRaBaCoCh;
    unsigned int nbr_of_ranks = 1;

    // Choose between Linear (simple) or DRAM (optimized) generator
    if (gen_id % 2 == 0) {
        // Even generators: Linear with large blocks
        storedGenerator = createLinear(duration, start_addr, end_addr,
                                      block_size, min_period, max_period,
                                      read_percent, data_limit);
        DPRINTF(TrafficGen, "Linear generator %s: block_size=%lu\n",
                name().c_str(), block_size);
    } else {
        // Odd generators: DRAM optimized
        storedGenerator = createDram(duration, start_addr, end_addr,
                                    block_size, min_period, max_period,
                                    read_percent, data_limit, num_seq_pkts,
                                    page_size, nbr_of_banks,
                                    nbr_of_banks_util, addr_mapping,
                                    nbr_of_ranks);
        DPRINTF(TrafficGen, "DRAM generator %s: seq_pkts=%u\n",
                name().c_str(), num_seq_pkts);
    if (gen_id == 0) {
        // DRAM generator with guaranteed non-overlapping range
        unsigned int num_seq_pkts = 16; // Number of sequential packets
        unsigned int page_size = 4096;  // 4KB page size
        unsigned int nbr_of_banks = 16;
        unsigned int nbr_of_banks_util = 16;
        enums::AddrMap addr_mapping = enums::RoRaBaCoCh;
        unsigned int nbr_of_ranks = 1;

        storedGenerator = createDram(
            duration,
            start_addr,
            end_addr,
            block_size,
            min_period,
            max_period,
            read_percent,
            data_limit,
            num_seq_pkts,
            page_size,
            nbr_of_banks,
            nbr_of_banks_util,
            addr_mapping,
            nbr_of_ranks
        );
    } else {
        // Random generator with non-overlapping range
        storedGenerator = createRandom(
            duration,
            start_addr,
            end_addr,
            block_size,
            min_period,
            max_period,
            read_percent,
            data_limit
        );
    }
}

void
BaseTrafficGen::transition()
{
    if (activeGenerator)
        activeGenerator->exit();

    activeGenerator = nextGenerator();

    if (activeGenerator) {
        const Tick duration = activeGenerator->duration;
        if (duration != MaxTick && duration != 0) {
            // we could have been delayed and not transitioned on the
            // exact tick when we were supposed to (due to back
            // pressure when sending a packet)
            nextTransitionTick = curTick() + duration;
        } else {
            nextTransitionTick = MaxTick;
        }

        activeGenerator->enter();
        nextPacketTick = activeGenerator->nextPacketTick(elasticReq, 0);
    } else {
        nextPacketTick = MaxTick;
        nextTransitionTick = MaxTick;
        assert(!updateEvent.scheduled());
    }
}

void
BaseTrafficGen::scheduleUpdate()
{
    // Has the generator run out of work? In that case, force a
    // transition if a transition period hasn't been configured.
    while (activeGenerator &&
           nextPacketTick == MaxTick && nextTransitionTick == MaxTick) {
        transition();
    }

    if (!activeGenerator)
        return;

    // schedule next update event based on either the next execute
    // tick or the next transition, which ever comes first
    const Tick nextEventTick = std::min(nextPacketTick, nextTransitionTick);

    DPRINTF(TrafficGen, "Next event scheduled at %lld\n", nextEventTick);

    // The next transition tick may be in the past if there was a
    // retry, so ensure that we don't schedule anything in the past.
    schedule(updateEvent, std::max(curTick(), nextEventTick));
}

void
BaseTrafficGen::start()
{
    createSimpleGenerator();
    transition();
    scheduleUpdate();
}

void
BaseTrafficGen::recvReqRetry()
{
    DPRINTF(TrafficGen, "Received retry\n");
    stats.numRetries++;
    retryReq();
}

void
BaseTrafficGen::retryReq()
{
    assert(retryPkt != NULL);
    assert(retryPktTick != 0);
    assert(!blockedWaitingResp);

    // attempt to send the packet, and if we are successful start up
    // the machinery again
    if (port.sendTimingReq(retryPkt)) {
        retryPkt = NULL;
        // remember how much delay was incurred due to back-pressure
        // when sending the request, we also use this to derive
        // the tick for the next packet
        Tick delay = curTick() - retryPktTick;
        retryPktTick = 0;
        stats.retryTicks += delay;

        if (drainState() != DrainState::Draining) {
            // Apply bandwidth control even during retries
            if (targetBandwidth > 0) {
                nextPacketTick = curTick() +
                    calculatePeriodForBandwidth(64);
            } else {
                nextPacketTick =
                    activeGenerator->nextPacketTick(elasticReq, delay);
            }
            scheduleUpdate();
        } else {
            // shut things down
            nextPacketTick = MaxTick;
            nextTransitionTick = MaxTick;
            signalDrainDone();
        }
    }
}

void
BaseTrafficGen::noProgress()
{
    fatal("BaseTrafficGen %s spent %llu ticks without making progress",
          name(), progressCheck);
}

BaseTrafficGen::StatGroup::StatGroup(statistics::Group *parent)
    : statistics::Group(parent),
      ADD_STAT(numSuppressed, statistics::units::Count::get(),
               "Number of suppressed packets to non-memory space"),
      ADD_STAT(numSuppressedByFilter, statistics::units::Count::get(),
               "Number of suppressed packets by address filter"),
      ADD_STAT(numPackets, statistics::units::Count::get(),
               "Number of packets generated"),
      ADD_STAT(numRetries, statistics::units::Count::get(),
               "Number of retries"),
      ADD_STAT(retryTicks, statistics::units::Tick::get(),
               "Time spent waiting due to back-pressure"),
      ADD_STAT(bytesRead, statistics::units::Byte::get(),
               "Number of bytes read"),
      ADD_STAT(bytesWritten, statistics::units::Byte::get(),
               "Number of bytes written"),
      ADD_STAT(totalReadLatency, statistics::units::Tick::get(),
               "Total latency of read requests"),
      ADD_STAT(totalWriteLatency, statistics::units::Tick::get(),
               "Total latency of write requests"),
      ADD_STAT(totalReads, statistics::units::Count::get(),
               "Total num of reads"),
      ADD_STAT(totalWrites, statistics::units::Count::get(),
               "Total num of writes"),
      ADD_STAT(avgReadLatency, statistics::units::Rate<
                    statistics::units::Tick,
                    statistics::units::Count>::get(),
               "Avg latency of read requests",
               totalReadLatency / totalReads),
      ADD_STAT(avgWriteLatency, statistics::units::Rate<
                    statistics::units::Tick,
                    statistics::units::Count>::get(),
               "Avg latency of write requests",
               totalWriteLatency / totalWrites),
      ADD_STAT(readBW, statistics::units::Rate<
                    statistics::units::Byte,
                    statistics::units::Second>::get(),
               "Read bandwidth", bytesRead / simSeconds),
      ADD_STAT(writeBW, statistics::units::Rate<
                    statistics::units::Byte,
                    statistics::units::Second>::get(),
               "Write bandwidth", bytesWritten / simSeconds)
{
}

std::shared_ptr<BaseGen>
BaseTrafficGen::createIdle(Tick duration)
{
    return std::shared_ptr<BaseGen>(new IdleGen(*this, requestorId,
                                                duration));
}

std::shared_ptr<BaseGen>
BaseTrafficGen::createExit(Tick duration)
{
    return std::shared_ptr<BaseGen>(new ExitGen(*this, requestorId,
                                                duration));
}

std::shared_ptr<BaseGen>
BaseTrafficGen::createLinear(Tick duration,
                             Addr start_addr, Addr end_addr, Addr blocksize,
                             Tick min_period, Tick max_period,
                             uint8_t read_percent, Addr data_limit)
{
    return std::shared_ptr<BaseGen>(new LinearGen(*this, requestorId,
                                                  duration, start_addr,
                                                  end_addr, blocksize,
                                                  system->cacheLineSize(),
                                                  min_period, max_period,
                                                  read_percent, data_limit));
}

std::shared_ptr<BaseGen>
BaseTrafficGen::createRandom(Tick duration,
                             Addr start_addr, Addr end_addr, Addr blocksize,
                             Tick min_period, Tick max_period,
                             uint8_t read_percent, Addr data_limit)
{
    return std::shared_ptr<BaseGen>(new RandomGen(*this, requestorId,
                                                  duration, start_addr,
                                                  end_addr, blocksize,
                                                  system->cacheLineSize(),
                                                  min_period, max_period,
                                                  read_percent, data_limit));
}

std::shared_ptr<BaseGen>
BaseTrafficGen::createDram(Tick duration,
                           Addr start_addr, Addr end_addr, Addr blocksize,
                           Tick min_period, Tick max_period,
                           uint8_t read_percent, Addr data_limit,
                           unsigned int num_seq_pkts, unsigned int page_size,
                           unsigned int nbr_of_banks,
                           unsigned int nbr_of_banks_util,
                           enums::AddrMap addr_mapping,
                           unsigned int nbr_of_ranks)
{
    return std::shared_ptr<BaseGen>(new DramGen(*this, requestorId,
                                                duration, start_addr,
                                                end_addr, blocksize,
                                                system->cacheLineSize(),
                                                min_period, max_period,
                                                read_percent, data_limit,
                                                num_seq_pkts, page_size,
                                                nbr_of_banks,
                                                nbr_of_banks_util,
                                                addr_mapping,
                                                nbr_of_ranks));
}

std::shared_ptr<BaseGen>
BaseTrafficGen::createDramRot(Tick duration,
                              Addr start_addr, Addr end_addr, Addr blocksize,
                              Tick min_period, Tick max_period,
                              uint8_t read_percent, Addr data_limit,
                              unsigned int num_seq_pkts,
                              unsigned int page_size,
                              unsigned int nbr_of_banks,
                              unsigned int nbr_of_banks_util,
                              enums::AddrMap addr_mapping,
                              unsigned int nbr_of_ranks,
                              unsigned int max_seq_count_per_rank)
{
    return std::shared_ptr<BaseGen>(new DramRotGen(*this, requestorId,
                                                   duration, start_addr,
                                                   end_addr, blocksize,
                                                   system->cacheLineSize(),
                                                   min_period, max_period,
                                                   read_percent, data_limit,
                                                   num_seq_pkts, page_size,
                                                   nbr_of_banks,
                                                   nbr_of_banks_util,
                                                   addr_mapping,
                                                   nbr_of_ranks,
                                                   max_seq_count_per_rank));
}

std::shared_ptr<BaseGen>
BaseTrafficGen::createHybrid(Tick duration,
                           Addr start_addr_dram, Addr end_addr_dram,
                           Addr blocksize_dram,
                           Addr start_addr_nvm, Addr end_addr_nvm,
                           Addr blocksize_nvm,
                           Tick min_period, Tick max_period,
                           uint8_t read_percent, Addr data_limit,
                           unsigned int num_seq_pkts_dram,
                           unsigned int page_size_dram,
                           unsigned int nbr_of_banks_dram,
                           unsigned int nbr_of_banks_util_dram,
                           unsigned int num_seq_pkts_nvm,
                           unsigned int buffer_size_nvm,
                           unsigned int nbr_of_banks_nvm,
                           unsigned int nbr_of_banks_util_nvm,
                           enums::AddrMap addr_mapping,
                           unsigned int nbr_of_ranks_dram,
                           unsigned int nbr_of_ranks_nvm,
                           uint8_t nvm_percent)
{
    return std::shared_ptr<BaseGen>(new HybridGen(*this, requestorId,
                                                duration, start_addr_dram,
                                                end_addr_dram, blocksize_dram,
                                                start_addr_nvm,
                                                end_addr_nvm, blocksize_nvm,
                                                system->cacheLineSize(),
                                                min_period, max_period,
                                                read_percent, data_limit,
                                                num_seq_pkts_dram,
                                                page_size_dram,
                                                nbr_of_banks_dram,
                                                nbr_of_banks_util_dram,
                                                num_seq_pkts_nvm,
                                                buffer_size_nvm,
                                                nbr_of_banks_nvm,
                                                nbr_of_banks_util_nvm,
                                                addr_mapping,
                                                nbr_of_ranks_dram,
                                                nbr_of_ranks_nvm,
                                                nvm_percent));
}

std::shared_ptr<BaseGen>
BaseTrafficGen::createNvm(Tick duration,
                           Addr start_addr, Addr end_addr, Addr blocksize,
                           Tick min_period, Tick max_period,
                           uint8_t read_percent, Addr data_limit,
                           unsigned int num_seq_pkts, unsigned int buffer_size,
                           unsigned int nbr_of_banks,
                           unsigned int nbr_of_banks_util,
                           enums::AddrMap addr_mapping,
                           unsigned int nbr_of_ranks)
{
    return std::shared_ptr<BaseGen>(new NvmGen(*this, requestorId,
                                                duration, start_addr,
                                                end_addr, blocksize,
                                                system->cacheLineSize(),
                                                min_period, max_period,
                                                read_percent, data_limit,
                                                num_seq_pkts, buffer_size,
                                                nbr_of_banks,
                                                nbr_of_banks_util,
                                                addr_mapping,
                                                nbr_of_ranks));
}

std::shared_ptr<BaseGen>
BaseTrafficGen::createStrided(
        Tick duration,
        Addr start_addr, Addr end_addr, Addr offset,
        Addr block_size, Addr superblock_size, Addr stride_size,
        Tick min_period, Tick max_period,
        uint8_t read_percent, Addr data_limit)
{
    return std::shared_ptr<BaseGen>(new StridedGen(
                                    *this, requestorId, duration,
                                    system->cacheLineSize(),
                                    start_addr, end_addr, offset,
                                    block_size, superblock_size, stride_size,
                                    min_period, max_period,
                                    read_percent, data_limit));
}

std::shared_ptr<BaseGen>
BaseTrafficGen::createTrace(Tick duration,
                            const std::string& trace_file, Addr addr_offset)
{
#if HAVE_PROTOBUF
    return std::shared_ptr<BaseGen>(
        new TraceGen(*this, requestorId, duration, trace_file, addr_offset));
#else
    panic("Can't instantiate trace generation without Protobuf support!\n");
#endif
}

bool
BaseTrafficGen::recvTimingResp(PacketPtr pkt)
{
    auto iter = waitingResp.find(pkt->req);

    if (iter == waitingResp.end()) {
        warn("%s: Received unexpected response for request %p\n",
             name(), pkt->req);
        delete pkt;
        return true;
    }

    assert(iter->second <= curTick());

    if (pkt->isWrite()) {
        ++stats.totalWrites;
        stats.bytesWritten += pkt->req->getSize();
        stats.totalWriteLatency += curTick() - iter->second;
    } else {
        ++stats.totalReads;
        stats.bytesRead += pkt->req->getSize();
        stats.totalReadLatency += curTick() - iter->second;
    }

    waitingResp.erase(iter);

    delete pkt;

    // Sends up the request if we were blocked
    if (blockedWaitingResp) {
        blockedWaitingResp = false;
        retryReq();
    }

    return true;
}

} // namespace gem5
