# Copyright (c) 2012-2013, 2015, 2018, 2023-2024 ARM Limited
# All rights reserved.
#
# The license below extends only to copyright in the software and shall
# not be construed as granting a license to any other intellectual
# property including but not limited to intellectual property relating
# to a hardware implementation of the functionality of the software
# licensed hereunder.  You may use the software subject to the license
# terms below provided that you ensure that this notice is replicated
# unmodified and in its entirety in all distributions of the software,
# modified or unmodified, in source code or in binary form.
#
# Copyright (c) 2005-2007 The Regents of The University of Michigan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from m5.objects.ClockedObject import ClockedObject
from m5.objects.Compressors import BaseCacheCompressor
from m5.objects.Prefetcher import BasePrefetcher
from m5.objects.ReplacementPolicies import *
from m5.objects.Tags import *
from m5.params import *
from m5.proxy import *
from m5.SimObject import SimObject


# Enum for cache clusivity, currently mostly inclusive or mostly
# exclusive.
class Clusivity(Enum):
    vals = ["mostly_incl", "mostly_excl"]


class WriteAllocator(SimObject):
    type = "WriteAllocator"
    cxx_header = "mem/cache/cache.hh"
    cxx_class = "gem5::WriteAllocator"

    # Control the limits for when the cache introduces extra delays to
    # allow whole-line write coalescing, and eventually switches to a
    # write-no-allocate policy.
    coalesce_limit = Param.Unsigned(
        2, "Consecutive lines written before delaying for coalescing"
    )
    no_allocate_limit = Param.Unsigned(
        12, "Consecutive lines written before skipping allocation"
    )

    delay_threshold = Param.Unsigned(
        8,
        "Number of delay quanta imposed on an "
        "MSHR with write requests to allow for "
        "write coalescing",
    )

    block_size = Param.Int(Parent.cache_line_size, "block size in bytes")


class BaseCache(ClockedObject):
    type = "BaseCache"
    abstract = True
    cxx_header = "mem/cache/base.hh"
    cxx_class = "gem5::BaseCache"

    size = Param.MemorySize("Capacity")
    assoc = Param.Unsigned("Associativity")

    tag_latency = Param.Cycles("Tag lookup latency")
    data_latency = Param.Cycles("Data access latency")
    response_latency = Param.Cycles("Latency for the return path on a miss")
    mshr_post_fill_cycles = Param.Cycles(
        0, "Cycles MSHR stays allocated after fill before deallocation"
    )
    mshr_clean_fill_cycles = Param.Cycles(
        0,
        "Override post-fill cycles for clean fills (no dirty WB).\n"
        "When non-zero, clean fills use this instead of "
        "mshr_post_fill_cycles.\n"
        "Models BOOM mshrs.scala: clean fills skip s_meta_clear + "
        "s_wb_req + s_wb_resp.",
    )
    mshr_post_fill_store_extra = Param.Cycles(
        0,
        "Extra post-fill MSHR slot cycles when fill has store targets.\n"
        "BOOM s_drain_rpq stores compete with STQ store_commit for the\n"
        "dcache write port, extending MSHR slot holding "
        "(mshrs.scala:362-373).",
    )
    boom_fill_wakeup_extra_hold = Param.Cycles(
        0, "Extra MSHR post-fill hold cycles for short fills (L2 hits)."
    )
    boom_fill_wakeup_miss_threshold = Param.Cycles(
        0, "Fill miss-latency threshold for boom_fill_wakeup_extra_hold."
    )
    mshr_dirty_wb_penalty_cycles = Param.Cycles(
        0, "Extra cycles MSHR stays allocated when fill causes dirty writeback"
    )
    mshr_store_replay_latency = Param.Cycles(
        0, "Cycles after WB unit start before store targets replayed from RPQ"
    )
    boom_spec_ld_miss_penalty = Param.Cycles(
        0,
        "Flat penalty (cycles) added to every load target completed from an "
        "MSHR fill.  Models BOOM speculative load wakeup failure: when a "
        "load enters the dcache pipeline, spec_ld_wakeup fires at s1 "
        "(lsu.scala:1288-1293) speculatively scheduling dependents.  On L1D "
        "miss, ld_miss squashes those dependents (lsu.scala:1415-1424), "
        "costing ~3-5 cycles of pipeline bubble per miss.  gem5 has no "
        "speculative load wakeup so rescheduledLoads=0; this penalty "
        "compensates for the missing pipeline cost.",
    )
    boom_spec_long_fill_threshold = Param.Cycles(
        0,
        "MSHR fill-duration threshold (cycles) above which the spec "
        "penalty is suppressed.  For long fills (L2 miss -> memory), "
        "the BOOM spec_ld_wakeup bubble is fully absorbed by the fill "
        "latency so the penalty is redundant.  0 = always apply.",
    )
    boom_spec_penalty_rtt_scale = Param.Cycles(
        0,
        "When > 0, enables continuous RTT-based scaling of the spec "
        "penalty instead of the binary threshold.  Penalty is linearly "
        "scaled: full at fillAge=0, zero at fillAge=rtt_scale.  This "
        "replaces boom_spec_long_fill_threshold when set.",
    )
    boom_spec_penalty_min_miss_lat = Param.Cycles(
        0,
        "Minimum MSHR miss latency (cycles) before the spec penalty "
        "is applied.  Misses resolved faster than this (e.g. L2 hits) "
        "skip the penalty.  0 = always apply (original behavior).",
    )
    boom_spec_penalty_low_pressure = Param.Cycles(
        0,
        "Spec penalty (cycles) used when MSHR pressure is below "
        "boom_spec_pressure_threshold.  Models that BOOM port contention "
        "(and thus effective spec wakeup cost) is lower when few MSHRs "
        "are active.  0 = disabled (always use boom_spec_ld_miss_penalty).",
    )
    boom_spec_pressure_threshold = Param.Unsigned(
        0,
        "numInService threshold for pressure-dependent spec penalty.  "
        "When numInService >= threshold, use boom_spec_ld_miss_penalty; "
        "otherwise use boom_spec_penalty_low_pressure.  0 = disabled.",
    )
    mshr_drain_load_cycles = Param.Cycles(
        0, "Per-load-target cycles in s_drain_rpq_loads (mshrs.scala:268-305)"
    )
    mshr_drain_load_base_cycles = Param.Cycles(
        0,
        "Base latency (cycles) added to EVERY load target from an MSHR "
        "fill, before the per-target stagger.",
    )
    mshr_drain_store_cycles = Param.Cycles(
        0, "Per-store-target cycles in s_drain_rpq (mshrs.scala:362-373)"
    )
    mshr_l2_pressure_mshr_threshold = Param.Unsigned(
        0,
        "L1 MSHR occupancy threshold above which the dirty-WB penalty "
        "is bumped by mshr_l2_pressure_extra_cycles, modeling observed "
        "L2 backpressure (when our own MSHRs are saturated, L2 grants "
        "are arriving slowly).  0 disables.",
    )
    mshr_l2_pressure_extra_cycles = Param.Cycles(
        0,
        "Cycles added to mshr_dirty_wb_penalty_cycles when L1 MSHR "
        "occupancy >= threshold.  Captures the L2-grant-time "
        "backpressure that gem5's standard L2 model under-counts.",
    )
    # --- Phase-3 L1D MSHR FSM walk (per-state cycles + shared arbiters)
    # ---------------------------------------------------------------------
    # Each fill walks through BOOM mshrs.scala state sequence with
    # per-state cycle costs.  Shared states (s_meta_*, s_wb_req,
    # s_commit_line) contend on per-cache arbiters; other states just
    # consume cycles.  When mshr_fsm_walk_enable is False the legacy
    # mshr_post_fill_cycles / mshr_dirty_wb_penalty / arbiter path is
    # used instead.
    mshr_fsm_walk_enable = Param.Bool(
        False, "Use Phase-3 per-state FSM walk on each fill"
    )

    # State durations (in cycles) ----------------------------------------
    mshr_fsm_meta_read_cycles = Param.Cycles(1, "s_meta_read")
    mshr_fsm_meta_resp_cycles = Param.Cycles(2, "s_meta_resp_1+2")
    mshr_fsm_meta_clear_cycles = Param.Cycles(1, "s_meta_clear")
    mshr_fsm_wb_req_cycles = Param.Cycles(1, "s_wb_req")
    mshr_fsm_wb_resp_cycles = Param.Cycles(13, "s_wb_resp wait")
    mshr_fsm_commit_line_cycles = Param.Cycles(8, "s_commit_line beats")
    mshr_fsm_meta_write_cycles = Param.Cycles(1, "s_meta_write_req")
    mshr_fsm_mem_finish_cycles = Param.Cycles(2, "s_mem_finish_1+2")
    mshr_fsm_drain_load_cycles = Param.Cycles(1, "per-load drain")
    mshr_fsm_drain_store_cycles = Param.Cycles(1, "per-store drain")

    # --- L1 MSHR FSM shared-arbiter modelling (Phase-b) ---
    # BOOM L1D MSHRs share meta_arb / refill_arb / wb_arb / commit-line
    # ports (boom/v3/lsu/mshrs.scala).  Even with mshrs=2 the FSMs
    # serialize through these arbiters on heavy back-to-back miss
    # streams such as MCS.  When > 0, this param holds a per-cache
    # shared arbiter for N cycles per fill: the post-fill release tick
    # is forced to be no earlier than the arbiter's busy-until tick,
    # effectively serializing MSHR finalization across all in-flight
    # MSHRs.
    mshr_fsm_arbiter_cycles = Param.Cycles(
        0,
        "Cycles per fill the L1 MSHR FSM holds the shared "
        "meta+refill+wb arbiter (0 disables; tune to match the serial "
        "portion of s_meta_*/s_wb_req/s_commit_line phases)",
    )

    enable_boom_wb_unit = Param.Bool(
        False,
        "When True, replace the constant dirty-WB penalty with a real "
        "BoomWritebackUnit FSM model: serialized WBs, structural "
        "FSM cycles + observed-RTT-derived grant latency.  Captures "
        "L2 backpressure variability without hand-tuned thresholds.",
    )
    boom_wb_unit_refill_cycles = Param.Cycles(
        4,
        "Beats per BOOM WB unit fill_buffer / active phase, equal to "
        "block_bytes / row_bytes (4 for mb 64B/16B, 2 for mg 64B/32B).",
    )
    boom_wb_unit_grant_baseline_cycles = Param.Cycles(
        13,
        "Baseline L2 round-trip latency in cycles -- subtracted from "
        "observed fill RTT to estimate the variable s_grant component "
        "of the WB FSM.  Default 13 = mb L2 tag(3)+data(5)+response(5).",
    )

    boom_wb_nack_penalty_cycles = Param.Cycles(
        0,
        "Per-event penalty (cycles) when an MSHR fill's dirty WB targets "
        "the same L1D set as the *previous* dirty-WB fill.  Models BOOM "
        "dcache.scala:730 s2_nack_wb: the WB unit holds the set's metadata "
        "lock, so any new miss to the same set is nacked and must retry "
        "through the LDQ wakeup queue (lsu.scala:520-535).  Fires only on "
        "consecutive same-set dirty-WB fills, so conflict-miss workloads "
        "(MCS) pay the penalty while sequential stores (STL2b) do not.",
    )

    boom_nack_retry_cycles = Param.Cycles(
        0,
        "Delay (in cycles) added to the dcache cpu-side retry signal when "
        "the cache transitions from blocked to unblocked.  Models BOOM "
        "dcache nack-retry pipeline cost: after a load is nacked at s2 "
        "(dcache.scala:726-732), it returns to the LDQ, must win "
        "re-arbitration (lsu.scala:817-870), and re-traverse the dcache "
        "pipeline (s0->s1->s2).  Total ~4 cycles per nack event.  gem5 "
        "retries instantly (curTick+1) by default; set to 4 for BOOM "
        "MediumBoom alignment.",
    )

    boom_silent_clean_evict = Param.Bool(
        False,
        "When True, suppress CleanEvict packets on L1D eviction of clean "
        "blocks.  BOOM TileLink does not send Release(BtoN) when evicting "
        "a line in Branch (read-only) state — the old line is silently "
        "overwritten (mshrs.scala:209,317-319: req_needs_wb=false skips "
        "s_wb_req).  gem5 MOESI sends CleanEvict through the write buffer, "
        "creating false wbuffer blocking on load-heavy workloads (ML2).",
    )

    warmup_percentage = Param.Percent(
        0, "Percentage of tags to be touched to warm up the cache"
    )

    max_miss_count = Param.Counter(
        0, "Number of misses to handle before calling exit"
    )

    mshrs = Param.Unsigned("Number of MSHRs (max outstanding requests)")
    demand_mshr_reserve = Param.Unsigned(1, "MSHRs reserved for demand access")
    tgts_per_mshr = Param.Unsigned("Max number of accesses per MSHR")
    write_buffers = Param.Unsigned(8, "Number of write buffers")

    is_read_only = Param.Bool(False, "Is this cache read only (e.g. inst)")

    prefetcher = Param.BasePrefetcher(NULL, "Prefetcher attached to cache")

    tags = Param.BaseTags(BaseSetAssoc(), "Tag store")
    replacement_policy = Param.BaseReplacementPolicy(
        LRURP(), "Replacement policy"
    )
    partitioning_manager = Param.PartitionManager(
        NULL, "Cache partitioning manager"
    )

    compressor = Param.BaseCacheCompressor(NULL, "Cache compressor.")
    replace_expansions = Param.Bool(
        True,
        "Apply replacement policy to "
        "decide which blocks should be evicted on a data expansion",
    )
    # When a block passes from uncompressed to compressed, it may become
    # co-allocatable with another existing entry of the same superblock,
    # so try move the block to co-allocate it
    move_contractions = Param.Bool(
        True, "Try to co-allocate blocks that contract"
    )

    sequential_access = Param.Bool(
        False, "Whether to access tags and data sequentially"
    )

    cpu_side = ResponsePort("Upstream port closer to the CPU and/or device")
    mem_side = RequestPort("Downstream port closer to memory")

    # DETMEM
    is_LLC = Param.Bool(False, "Is this cache an LLC")

    is_iCache = Param.Bool(False, "Is this cache an instruction cache")

    is_dCache = Param.Bool(False, "Is this cache a data cache")

    cpu_id = Param.Int(0, "CPU ID for this cache")

    addr_ranges = VectorParam.AddrRange(
        [AllMemory], "Address range for the CPU-side port (to allow striping)"
    )

    system = Param.System(Parent.any, "System we belong to")

    # Determine if this cache sends out writebacks for clean lines, or
    # simply clean evicts. If this cache does not have a downstream cache,
    # the cache should not writeback clean lines not to waste memory
    # bandwidth. If this cache has a downstream cache whose clusivity is
    # mostly exclusive (i.e., victim cache), this shoule be set to True.
    # If not, there will never be any spills from read-only caches (e.g.,
    # L1I cache, MMU cache of ARM) to the downstream cache.
    # In case of the downstream cache is mostly inclusive, this should be
    # set to False.
    writeback_clean = Param.Bool(False, "Writeback clean lines")

    # Control whether this cache should be mostly inclusive or mostly
    # exclusive with respect to upstream caches. The behaviour on a
    # fill is determined accordingly. For a mostly inclusive cache,
    # blocks are allocated on all fill operations. Thus, L1 caches
    # should be set as mostly inclusive even if they have no upstream
    # caches. In the case of a mostly exclusive cache, fills are not
    # allocating unless they came directly from a non-caching source,
    # e.g. a table walker. Additionally, on a hit from an upstream
    # cache a line is dropped for a mostly exclusive cache.
    clusivity = Param.Clusivity("mostly_incl", "Clusivity with upstream cache")

    # The write allocator enables optimizations for streaming write
    # accesses by first coalescing writes and then avoiding allocation
    # in the current cache. Typically, this would be enabled in the
    # data cache.
    write_allocator = Param.WriteAllocator(NULL, "Write allocator")
    flush_on_stat_reset = Param.Bool(
        False,
        "Invalidate all cache lines when stats are reset (at workbegin).\n"
        "Matches BOOM verilator cold-start behaviour where data arrays\n"
        "are not pre-warmed in the cache hierarchy before ROI.",
    )


class Cache(BaseCache):
    type = "Cache"
    cxx_header = "mem/cache/cache.hh"
    cxx_class = "gem5::Cache"


class NoncoherentCache(BaseCache):
    type = "NoncoherentCache"
    cxx_header = "mem/cache/noncoherent_cache.hh"
    cxx_class = "gem5::NoncoherentCache"

    # This is typically a last level cache and any clean
    # writebacks would be unnecessary traffic to the main memory.
    writeback_clean = False
