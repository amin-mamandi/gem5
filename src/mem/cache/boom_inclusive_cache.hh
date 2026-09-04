/*
 * Copyright (c) 2026 The Regents of the University of California.
 * All rights reserved.
 *
 * Phase-1+2 BOOM-faithful InclusiveCache: subclasses gem5's Cache and
 * adds Scheduler arbitration + BankedStore sub-bank conflict modelling +
 * per-target staggering on MSHR responses.  Phase 2 also tracks the
 * InclusiveCache MSHR FSM s_*, w_* flag set per outstanding MSHR.
 *
 * See sifive.blocks.inclusivecache.{Scheduler,MSHR,BankedStore} for
 * ground truth.
 */

#ifndef __MEM_CACHE_BOOM_INCLUSIVE_CACHE_HH__
#define __MEM_CACHE_BOOM_INCLUSIVE_CACHE_HH__

#include <unordered_map>
#include <vector>

#include "base/types.hh"
#include "mem/cache/cache.hh"

namespace gem5
{

class CacheBlk;
class MSHR;
struct BoomInclusiveCacheParams;

/**
 * Phase-1+2 InclusiveCache port.
 *
 * Phase 1 -- Scheduler arbitration + BankedStore sub-bank reservation:
 *  Hit responses and MSHR fill responses must reserve (a) one sub-bank
 *  per access and (b) a Scheduler slot, both modelled as per-cache
 *  busy-until ticks.  This serialises e.g. six ready MSHRs that would
 *  otherwise complete in the same tick.
 *
 * Phase 2 -- per-target staggering + MSHR FSM tracking:
 *  Stock Cache::serviceMSHRTargets schedules every target reply at the
 *  same `completion_time` (= pkt->headerDelay + responseLatency + ...),
 *  bunching N replies together.  The real InclusiveCache SourceD pipe
 *  drains one target per Scheduler cycle.  We override the function so
 *  each FromCPU target reserves its own Scheduler slot, producing a
 *  staggered schedTimingResp time per target.
 *
 *  The per-MSHR `BoomMshrFsm` struct tracks the s_*, w_* flag set from
 *  MSHR.scala.  In this phase the flags are observed but do not yet
 *  block scheduler arbitration (Phase 3); they exist for stat plumbing
 *  and as the substrate for future channel-aware modelling.
 */
class BoomInclusiveCache : public Cache
{
  public:
    BoomInclusiveCache(const BoomInclusiveCacheParams &p);

  protected:
    /// Override to gate the hit response on bank+scheduler resources.
    void handleTimingReqHit(PacketPtr pkt, CacheBlk *blk,
                            Tick request_time) override;

    /// Override completely: per-target staggered schedTimingResp.
    void serviceMSHRTargets(MSHR *mshr, const PacketPtr pkt,
                            CacheBlk *blk) override;


  private:
    // ---- BankedStore -----------------------------------------------------
    /// Number of sub-banks in the data SRAM.
    const unsigned numSubBanks;
    /// Granularity (bytes) of a single sub-bank lane.
    const unsigned writeBytesParam;
    /// Cycles a sub-bank stays busy per access.
    const Cycles bankAccessCycles;
    /// busyUntil[bank] = earliest tick that bank is free again.
    std::vector<Tick> bankBusyUntil;

    /// Map a packet's block address to a starting sub-bank index.
    unsigned bankIndexFor(Addr addr) const;

    /**
     * Reserve `how_many` sub-banks starting from `earliest`.  Returns the
     * tick at which the reservation finishes (= bank free again).
     */
    Tick reserveBanks(Addr addr, Tick earliest, unsigned how_many);

    // ---- Scheduler arbitration ------------------------------------------
    const Cycles schedulerArbCycles;
    /// Earliest tick the Scheduler can fire its next pick.
    Tick schedulerBusyUntil;

    Tick reserveSchedulerSlot(Tick earliest);

    // ---- MSHR FSM (Phase 2) ---------------------------------------------
    /**
     * Mirrors sifive.blocks.inclusivecache.MSHR.scala lines 124-142.
     * `s_*` = scheduled (true once action complete), `w_*` = waiting
     * (true once response observed).  An MSHR is only allowed to advance
     * its scheduler.valid when at least one s_*, w_* bit is FALSE.
     */
    struct BoomMshrFsm
    {
        // Schedule flags (true = action already done / not needed)
        bool s_rprobe       = true;
        bool s_release      = true;
        bool s_pprobe       = true;
        bool s_acquire      = true;
        bool s_flush        = true;
        bool s_probeack     = true;
        bool s_grantack     = true;
        bool s_execute      = true;
        bool s_writeback    = true;

        // Wait flags (true = response observed / not needed)
        bool w_rprobeackfirst = true;
        bool w_rprobeacklast  = true;
        bool w_releaseack     = true;
        bool w_pprobeackfirst = true;
        bool w_pprobeacklast  = true;
        bool w_pprobeack      = true;
        bool w_grantfirst     = true;
        bool w_grantlast      = true;
        bool w_grant          = true;
        bool w_grantack       = true;

        /// `no_wait` from MSHR.scala:215.
        bool noWait() const {
            return w_rprobeacklast && w_releaseack && w_grantlast &&
                   w_pprobeacklast && w_grantack;
        }

        /// `io.schedule.valid` from MSHR.scala:225-228.
        bool scheduleValid() const {
            return !s_acquire || !s_release || !s_pprobe || !s_rprobe ||
                   !s_probeack || !s_grantack || !s_execute ||
                   !s_writeback || !s_flush;
        }
    };

    /// Per-MSHR FSM, keyed on the gem5 MSHR pointer.  Allocated lazily
    /// on first lookup and cleared when the MSHR deallocates (via
    /// `noWait()` reaching true on the final scheduler tick).
    std::unordered_map<const MSHR *, BoomMshrFsm> mshrFsmTable;

    /**
     * Get/allocate the FSM for an MSHR.  Called from response paths.
     * Initial allocation sets the MSHR up as a fresh demand miss:
     *   s_acquire = false (need to send Acquire)
     *   w_grantfirst = w_grantlast = w_grant = false (waiting on Grant)
     *   s_execute = false (need to drive SourceD reply)
     *   s_writeback = false (need to write directory)
     */
    BoomMshrFsm &getOrAllocFsm(const MSHR *mshr);

    /// Drop FSM entry once the MSHR is fully retired.
    void retireFsm(const MSHR *mshr);


    // ---- L2 grant pressure (B.1) ---------------------------------------
    /// Cycles added per active L2 MSHR to each grant.
    const Cycles l2GrantPressureCycles;

    /// Compute the current grant pressure in ticks.  Uses
    /// mshrQueue.numAllocated() as the occupancy signal.
    Tick currentGrantPressureTicks() const;

    // ---- Phase-1/2 stat plumbing ---------------------------------------
    uint64_t bankConflictCycles = 0;
    uint64_t schedulerStallCycles = 0;
    uint64_t mshrTargetStaggerCycles = 0;
};

} // namespace gem5

#endif // __MEM_CACHE_BOOM_INCLUSIVE_CACHE_HH__
