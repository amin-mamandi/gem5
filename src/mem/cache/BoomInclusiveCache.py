# Copyright (c) 2026 The Regents of the University of California
# All Rights Reserved.
#
# Phase-1 BOOM-faithful InclusiveCache port for gem5.
# Models Scheduler arbitration + BankedStore sub-bank conflicts on top of
# the stock Cache. See sifive.blocks.inclusivecache.{Scheduler,BankedStore}.

from m5.objects.Cache import Cache
from m5.params import *


class BoomInclusiveCache(Cache):
    type = "BoomInclusiveCache"
    cxx_header = "mem/cache/boom_inclusive_cache.hh"
    cxx_class = "gem5::BoomInclusiveCache"

    # --- BankedStore (sub-banked data SRAM) ---
    # InclusiveCache splits the data SRAM into:
    #   numBanks = (portFactor * max(innerBeatBytes, outerBeatBytes))
    #              / writeBytes
    # Concurrent SourceD/SinkD/SourceC accesses can proceed in parallel
    # only if they hit DIFFERENT sub-banks; otherwise priority ordering
    # serializes them.  This phase-1 port models the contention by
    # reserving one bank-per-access for `bank_access_cycles` cycles.
    port_factor = Param.Unsigned(
        4,
        "InclusiveCacheMicroParameters portFactor (default 4 for Boom mb/mg)",
    )
    write_bytes = Param.Unsigned(
        8, "InclusiveCacheMicroParameters writeBytes (data SRAM granularity)"
    )
    inner_beat_bytes = Param.Unsigned(
        8, "Inner (l2bus) TileLink beat width in bytes"
    )
    outer_beat_bytes = Param.Unsigned(
        8, "Outer (membus) TileLink beat width in bytes"
    )
    bank_access_cycles = Param.Cycles(
        1, "Cycles a sub-bank stays busy per access (one SRAM port turn)"
    )

    # --- Scheduler arbitration ---
    # InclusiveCache.Scheduler picks at most ONE MSHR per cycle to advance
    # (round-robin priority).  gem5's outgoing port already serializes
    # outbound misses; this knob additionally serializes inbound responses
    # from the SourceD pipeline so 6 ready MSHRs do NOT all complete in the
    # same tick.
    scheduler_arb_cycles = Param.Cycles(
        1, "Cycles between consecutive MSHR scheduler fires"
    )

    # SourceD response pipeline depth in cycles; this is already covered
    # by `tag_latency + data_latency + response_latency` for hits, but is
    # exposed here for future explicit-pipeline modelling.
    sourced_pipeline_cycles = Param.Cycles(
        5,
        "InclusiveCache SourceD pipeline depth (s1 + 2c BankedStore + merge)",
    )

    # outerLatencyCycles guess used by the InclusiveCache scheduler to
    # decide when speculative grants/refills can fire.  Not load-bearing
    # for behaviour today; reserved for phase-2 MSHR FSM modelling.

    # --- L2 grant pressure (B.1) ---
    # When > 0, every cpu-side hit response and every MSHR-target reply
    # gets `numActiveMshrs * l2_grant_pressure_cycles` extra cycles
    # added to its completion time, modelling the real BOOM L2 grant
    # path slowing under directory + DRAM-queue backpressure.  The
    # pressure feeds back through observedFillRtt to the L1's
    # BoomWritebackUnit (Option C) so s_wb_resp scales with L2 load.
    l2_grant_pressure_cycles = Param.Cycles(
        0,
        "Cycles added to each L2 hit/fill reply per active L2 MSHR; "
        "models L2 directory + DRAM-queue backpressure",
    )

    mem_cycles_estimate = Param.Cycles(
        40, "WithInclusiveCache outerLatencyCycles default"
    )
