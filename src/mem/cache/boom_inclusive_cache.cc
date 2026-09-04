/*
 * Copyright (c) 2026 The Regents of the University of California.
 * All rights reserved.
 *
 * Phase-1+2 BOOM-faithful InclusiveCache implementation.  See header.
 */

#include "mem/cache/boom_inclusive_cache.hh"

#include <algorithm>

#include "base/logging.hh"
#include "debug/Cache.hh"
#include "debug/CacheVerbose.hh"
#include "mem/cache/cache_blk.hh"
#include "mem/cache/mshr.hh"
#include "mem/packet.hh"
#include "params/BoomInclusiveCache.hh"

namespace gem5
{

BoomInclusiveCache::BoomInclusiveCache(const BoomInclusiveCacheParams &p)
    : Cache(p),
      numSubBanks(std::max<unsigned>(
          1u,
          (p.port_factor * std::max(p.inner_beat_bytes, p.outer_beat_bytes))
              / std::max<unsigned>(1u, p.write_bytes))),
      writeBytesParam(std::max<unsigned>(1u, p.write_bytes)),
      bankAccessCycles(p.bank_access_cycles),
      bankBusyUntil(numSubBanks, 0),
      schedulerArbCycles(p.scheduler_arb_cycles),
      schedulerBusyUntil(0),
      l2GrantPressureCycles(p.l2_grant_pressure_cycles)
{
}

Tick
BoomInclusiveCache::currentGrantPressureTicks() const
{
    if (l2GrantPressureCycles == Cycles(0)) return 0;
    const int n = mshrQueue.numAllocated();
    if (n <= 0) return 0;
    return cyclesToTicks(Cycles(static_cast<unsigned>(n) *
                                static_cast<unsigned>(l2GrantPressureCycles)));
}

unsigned
BoomInclusiveCache::bankIndexFor(Addr addr) const
{
    return (addr / writeBytesParam) % numSubBanks;
}

// Reserve `how_many` sub-banks starting at `earliest`.
// IMPORTANT: returns `group_start` (when the access can BEGIN) -- the
// bank-occupancy duration is already accounted for by gem5's data_latency
// param.  The reservation is ONLY for contention modelling: if a previous
// access still has the bank busy, this call's `group_start` is pushed
// past `earliest`, capturing the wait.  Returning `group_end` would
// double-charge every access by bankAccessCycles even with no contention,
// inflating L2-hit benches like MIM/MIM2.
Tick
BoomInclusiveCache::reserveBanks(Addr addr, Tick earliest, unsigned how_many)
{
    if (how_many == 0) return earliest;
    if (how_many > numSubBanks) how_many = numSubBanks;

    const Tick burst = cyclesToTicks(bankAccessCycles);
    const unsigned start_bank = bankIndexFor(addr);

    Tick group_start = earliest;
    for (unsigned i = 0; i < how_many; ++i) {
        unsigned b = (start_bank + i) % numSubBanks;
        if (bankBusyUntil[b] > group_start)
            group_start = bankBusyUntil[b];
    }

    const Tick group_end = group_start + burst;

    for (unsigned i = 0; i < how_many; ++i) {
        unsigned b = (start_bank + i) % numSubBanks;
        bankBusyUntil[b] = group_end;
    }

    if (group_start > earliest)
        bankConflictCycles += ticksToCycles(group_start - earliest);

    return group_start;
}

// Reserve a Scheduler slot starting at `earliest`.  Same fix as above:
// return `start` (when the slot fires) so callers only see *contention*
// stall, not the baseline 1c per slot.  The slot still occupies the
// scheduler for `schedulerArbCycles` going forward, so consecutive
// callers see the contention.
Tick
BoomInclusiveCache::reserveSchedulerSlot(Tick earliest)
{
    const Tick burst = cyclesToTicks(schedulerArbCycles);
    Tick start = std::max(earliest, schedulerBusyUntil);
    if (start > earliest)
        schedulerStallCycles += ticksToCycles(start - earliest);
    schedulerBusyUntil = start + burst;
    return start;
}

BoomInclusiveCache::BoomMshrFsm &
BoomInclusiveCache::getOrAllocFsm(const MSHR *mshr)
{
    auto it = mshrFsmTable.find(mshr);
    if (it != mshrFsmTable.end())
        return it->second;
    auto &fsm = mshrFsmTable[mshr];
    // Initial state for a fresh demand miss: must Acquire from outer,
    // wait for Grant, then drive SourceD reply, then write directory.
    // Probe-related flags stay TRUE (no inner-probe needed at L2 for
    // a fresh miss in a non-multicore mb config).
    fsm.s_acquire     = false;
    fsm.w_grantfirst  = false;
    fsm.w_grantlast   = false;
    fsm.w_grant       = false;
    fsm.s_execute     = false;
    fsm.s_writeback   = false;
    return fsm;
}

void
BoomInclusiveCache::retireFsm(const MSHR *mshr)
{
    mshrFsmTable.erase(mshr);
}


void
BoomInclusiveCache::handleTimingReqHit(PacketPtr pkt, CacheBlk *blk,
                                        Tick request_time)
{
    // SinkC writeback path: BOOM's BankedStore (BankedStore.scala:97-99)
    // priority is sinkC > sourceC > sinkD > sourceDw > sourceDr.
    // When L1D writes back a (dirty) line, SinkC writes all inner beats
    // to BankedStore sub-banks with highest priority, blocking concurrent
    // sourceDr reads (SourceD fill-data responses to L1D).  gem5 was
    // previously not modelling this contention, making L2 hit responses
    // too fast under heavy writeback traffic (MC, MCS benchmarks).
    if (pkt && pkt->isWriteback()) {
        reserveBanks(pkt->getBlockAddr(blkSize), request_time, numSubBanks);
    }

    // Hit response uses the SourceD pipeline: reserve all sub-banks AND
    // a Scheduler slot so that consecutive hits naturally serialise.
    if (pkt && pkt->needsResponse()) {
        Tick t = request_time;
        t = reserveBanks(pkt->getBlockAddr(blkSize), t, numSubBanks);
        t = reserveSchedulerSlot(t);
        // B.1: add grant pressure -- L2 directory/DRAM-queue backup
        // slows the response under heavy MSHR occupancy.
        t += currentGrantPressureTicks();
        request_time = std::max(request_time, t);
    }
    Cache::handleTimingReqHit(pkt, blk, request_time);
}

// --------------------------------------------------------------------------
// serviceMSHRTargets -- copy of Cache::serviceMSHRTargets with two changes:
//   1. each FromCPU target reserves its own Scheduler+bank slot, producing
//      a per-target staggered completion_time
//   2. once the MSHR finishes, retire its BoomMshrFsm entry
// The body is otherwise byte-for-byte identical to gem5's stock
// Cache::serviceMSHRTargets so that LockedRMW + snoop semantics are
// preserved.  When upstream gem5 changes that function, this will need
// to be re-synced.
// --------------------------------------------------------------------------
void
BoomInclusiveCache::serviceMSHRTargets(MSHR *mshr, const PacketPtr pkt,
                                        CacheBlk *blk)
{
    QueueEntry::Target *initial_tgt = mshr->getTarget();
    const int initial_offset = initial_tgt->pkt->getOffset(blkSize);

    const bool is_error = pkt->isError();
    bool is_invalidate = pkt->isInvalidate() && !mshr->wasWholeLineWrite;

    bool from_core = false;
    bool from_pref = false;

    if (pkt->cmd == MemCmd::LockedRMWWriteResp) {
        assert(initial_tgt->pkt->cmd == MemCmd::LockedRMWReadReq);
        delete initial_tgt->pkt;
        initial_tgt->pkt = nullptr;
        mshr->popTarget();
        initial_tgt = nullptr;
    }

    // Phase 2: observe the Grant arrival on the MSHR FSM.  This represents
    // SinkD's first/last beat completing for the request.
    if (mshr) {
        auto &fsm = getOrAllocFsm(mshr);
        fsm.w_grantfirst = true;
        fsm.w_grantlast  = true;
        fsm.w_grant      = true;
    }

    MSHR::TargetList targets = mshr->extractServiceableTargets(pkt);

    // Phase 2: track per-target scheduler/bank stagger.  The first target
    // pays the resource arbitration starting at curTick(); each subsequent
    // target advances along the same scheduler.  This mirrors SourceD
    // draining one target per Scheduler cycle.
    Addr blk_addr = mshr->blkAddr;
    unsigned tgt_idx = 0;
    Tick base_now = curTick();

    for (auto &target: targets) {
        Packet *tgt_pkt = target.pkt;
        switch (target.source) {
          case MSHR::Target::FromCPU:
          {
            from_core = true;

            Tick completion_time;
            completion_time = pkt->headerDelay;

            // Phase 2: per-target scheduler+bank reservation.  We reserve
            // FROM the response's natural completion baseline so the
            // stagger is on top of, not in place of, gem5's response
            // latency.  base_response_tick is when target N's response
            // would naturally be ready under the stock model.
            const Tick natural_resp_tick = base_now + completion_time +
                cyclesToTicks(responseLatency);
            Tick gated =
                reserveBanks(blk_addr, natural_resp_tick, numSubBanks);
            gated = reserveSchedulerSlot(gated);
            // B.1: add grant pressure to per-target reply.
            gated += currentGrantPressureTicks();
            const Tick stagger_extra = (gated > natural_resp_tick)
                ? (gated - natural_resp_tick)
                : 0;
            mshrTargetStaggerCycles += ticksToCycles(stagger_extra);

            if (tgt_pkt->cmd.isSWPrefetch()) {
                if (tgt_pkt->needsWritable()) {
                    assert(blk);
                    blk->setCoherenceBits(CacheBlk::DirtyBit);
                    panic_if(isReadOnly,
                             "Prefetch exclusive requests from "
                             "read-only cache %s\n", name());
                }
                delete tgt_pkt;
                break; // skip response
            }

            if (tgt_pkt->cmd == MemCmd::WriteLineReq) {
                assert(!is_error);
                assert(blk);
                assert(blk->isSet(CacheBlk::WritableBit));
            }

            if (blk && blk->isValid() &&
                (!mshr->isForward || !pkt->hasData())) {
                satisfyRequest(tgt_pkt, blk, true, mshr->hasPostDowngrade());

                int transfer_offset =
                    tgt_pkt->getOffset(blkSize) - initial_offset;
                if (transfer_offset < 0)
                    transfer_offset += blkSize;

                completion_time += clockEdge(responseLatency) +
                    (transfer_offset ? pkt->payloadDelay : 0) +
                    stagger_extra;

                assert(!tgt_pkt->req->isUncacheable());
                assert(tgt_pkt->req->requestorId() <
                       system->maxRequestors());
                stats.cmdStats(tgt_pkt)
                    .missLatency[tgt_pkt->req->requestorId()] +=
                    completion_time - target.recvTime;

                if (tgt_pkt->cmd == MemCmd::LockedRMWReadReq) {
                    mshr->updateLockedRMWReadTarget(tgt_pkt);
                    blk->clearCoherenceBits(CacheBlk::WritableBit);
                    blk->clearCoherenceBits(CacheBlk::ReadableBit);
                }
            } else if (pkt->cmd == MemCmd::UpgradeFailResp) {
                assert(tgt_pkt->cmd == MemCmd::StoreCondReq ||
                       tgt_pkt->cmd == MemCmd::StoreCondFailReq ||
                       tgt_pkt->cmd == MemCmd::SCUpgradeFailReq);
                completion_time += clockEdge(responseLatency) +
                    pkt->payloadDelay + stagger_extra;
                tgt_pkt->req->setExtraData(0);
            } else if (pkt->cmd == MemCmd::LockedRMWWriteResp) {
                completion_time = clockEdge(responseLatency) + stagger_extra;
            } else {
                if (is_invalidate && blk && blk->isValid())
                    invalidateBlock(blk);
                completion_time += clockEdge(responseLatency) +
                    pkt->payloadDelay + stagger_extra;
                if (!is_error) {
                    if (pkt->isRead()) {
                        assert(pkt->matchAddr(tgt_pkt));
                        assert(pkt->getSize() >= tgt_pkt->getSize());
                        tgt_pkt->setData(pkt->getConstPtr<uint8_t>());
                    } else {
                        assert(!tgt_pkt->hasRespData());
                    }
                }
                tgt_pkt->copyResponderFlags(pkt);
            }
            tgt_pkt->makeTimingResponse();
            if (is_error)
                tgt_pkt->copyError(pkt);
            if (tgt_pkt->cmd == MemCmd::ReadResp &&
                (is_invalidate || mshr->hasPostInvalidate())) {
                tgt_pkt->cmd = MemCmd::ReadRespWithInvalidate;
                DPRINTF(Cache, "%s: updated cmd to %s\n", __func__,
                        tgt_pkt->print());
            }
            tgt_pkt->headerDelay = tgt_pkt->payloadDelay = 0;
            cpuSidePort.schedTimingResp(tgt_pkt, completion_time);
            ++tgt_idx;
            break;
          }

          case MSHR::Target::FromPrefetcher:
            assert(tgt_pkt->cmd == MemCmd::HardPFReq);
            from_pref = true;
            delete tgt_pkt;
            break;

          case MSHR::Target::FromSnoop:
            assert(!is_error);
            DPRINTF(Cache, "processing deferred snoop...\n");
            assert(!is_invalidate || pkt->cmd == MemCmd::InvalidateResp ||
                   pkt->req->isCacheMaintenance() ||
                   mshr->hasPostInvalidate());
            // Snoop targets use SourceC (probe response) not SourceD;
            // we don't gate them with the scheduler/bank model in Phase 2
            // (deferred to Phase 3).  Reuse Cache::handleSnoop for the
            // exact gem5 behaviour.
            handleSnoop(tgt_pkt, blk, true, true, mshr->hasPostInvalidate());
            break;

          default:
            panic("Illegal target->source enum %d\n", target.source);
        }
    }

    if (blk && !from_core && from_pref)
        blk->setPrefetched();

    if (!mshr->hasLockedRMWReadTarget()) {
        maintainClusivity(targets.hasFromCache, blk);

        if (blk && blk->isValid()) {
            if (is_invalidate || mshr->hasPostInvalidate()) {
                invalidateBlock(blk);
            } else if (mshr->hasPostDowngrade()) {
                blk->clearCoherenceBits(CacheBlk::WritableBit);
            }
        }
    }

    // Phase 2: mark this MSHR done in the FSM model and retire it.
    if (mshr) {
        auto &fsm = getOrAllocFsm(mshr);
        fsm.s_execute   = true;
        fsm.s_writeback = true;
        if (fsm.noWait())
            retireFsm(mshr);
    }
}

} // namespace gem5
