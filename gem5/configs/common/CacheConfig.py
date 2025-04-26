# Copyright (c) 2012-2013, 2015-2016 ARM Limited
# Copyright (c) 2020 Barkhausen Institut
# All rights reserved
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
# Copyright (c) 2010 Advanced Micro Devices, Inc.
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

# Configure the M5 cache hierarchy config in one place
#

from common import ObjectList
from common.Caches import *

import m5
from m5.objects import *

from gem5.isas import ISA


def _get_hwp(hwp_option):
    if hwp_option == None:
        return NULL

    hwpClass = ObjectList.hwp_list.get(hwp_option)
    return hwpClass()


def _get_cache_opts(level, options):
    opts = {}

    size_attr = f"{level}_size"
    if hasattr(options, size_attr):
        opts["size"] = getattr(options, size_attr)

    assoc_attr = f"{level}_assoc"
    if hasattr(options, assoc_attr):
        opts["assoc"] = getattr(options, assoc_attr)

    # Bank configuration
    enable_banks_attr = f"{level}_enable_banks"
    if hasattr(options, enable_banks_attr):
        opts["enable_banks"] = getattr(options, enable_banks_attr)
        
    num_banks_attr = f"{level}_num_banks" 
    if hasattr(options, num_banks_attr):
        opts["num_banks"] = getattr(options, num_banks_attr)
        
    intlv_bit_attr = f"{level}_intlv_bit"
    if hasattr(options, intlv_bit_attr):
        opts["bank_intlv_high_bit"] = getattr(options, intlv_bit_attr)
    
    # Latency parameters
    tag_latency_attr = f"{level}_tag_lat"
    if hasattr(options, tag_latency_attr):
        opts["tag_latency"] = getattr(options, tag_latency_attr)
        
    data_latency_attr = f"{level}_data_lat"
    if hasattr(options, data_latency_attr):
        opts["data_latency"] = getattr(options, data_latency_attr)
        
    write_latency_attr = f"{level}_write_lat"
    if hasattr(options, write_latency_attr):
        opts["write_latency"] = getattr(options, write_latency_attr)
        
    response_latency_attr = f"{level}_resp_lat"
    if hasattr(options, response_latency_attr):
        opts["response_latency"] = getattr(options, response_latency_attr)
    
    # Prefetcher configuration
    prefetcher_degree_attr = f"{level}_hwp_deg"
    if hasattr(options, prefetcher_degree_attr):
        hwp_opts["degree"] = getattr(options, prefetcher_degree_attr)
        
    prefetcher_latency_attr = f"{level}_hwp_lat"
    if hasattr(options, prefetcher_latency_attr):
        hwp_opts["latency"] = getattr(options, prefetcher_latency_attr)
        
    prefetcher_qs_attr = f"{level}_hwp_qs"
    if hasattr(options, prefetcher_qs_attr):
        hwp_opts["queue_size"] = getattr(options, prefetcher_qs_attr)
        
    prefetcher_attr = f"{level}_hwp_type"
    if hasattr(options, prefetcher_attr):
        opts["prefetcher"] = _get_hwp(getattr(options, prefetcher_attr))

    return opts


def config_cache(options, system):
    if options.external_memory_system and (options.caches or options.l2cache):
        print("External caches and internal caches are exclusive options.\n")
        sys.exit(1)

    if options.external_memory_system:
        ExternalCache = ExternalCacheFactory(options.external_memory_system)

    if options.cpu_type == "O3_ARM_v7a_3":
        try:
            import cores.arm.O3_ARM_v7a as core
        except:
            print("O3_ARM_v7a_3 is unavailable. Did you compile the O3 model?")
            sys.exit(1)

        dcache_class, icache_class, l2_cache_class, walk_cache_class = (
            core.O3_ARM_v7a_DCache,
            core.O3_ARM_v7a_ICache,
            core.O3_ARM_v7aL2,
            None,
        )
    elif options.cpu_type == "HPI":
        try:
            import cores.arm.HPI as core
        except:
            print("HPI is unavailable.")
            sys.exit(1)

        dcache_class, icache_class, l2_cache_class, walk_cache_class = (
            core.HPI_DCache,
            core.HPI_ICache,
            core.HPI_L2,
            None,
        )
    else:
        dcache_class, icache_class, l2_cache_class, walk_cache_class = (
            L1_DCache,
            L1_ICache,
            L2Cache,
            None,
        )

    # Set the cache line size of the system
    system.cache_line_size = options.cacheline_size

    # If elastic trace generation is enabled, make sure the memory system is
    # minimal so that compute delays do not include memory access latencies.
    # Configure the compulsory L1 caches for the O3CPU, do not configure
    # any more caches.
    if options.l2cache and options.elastic_trace_en:
        fatal("When elastic trace is enabled, do not configure L2 caches.")

    num_l2caches = options.num_l2caches

    if options.l2cache:
        if options.num_cpus % num_l2caches != 0:
            fatal("The number of L2 caches must be a submultiple of the ",
                  "number of cores.")
        ##########################################
        # num_cores = 4
        # total_ways = 16  # Assuming assoc=16
        # ways_for_core0 = total_ways // 2  # Half of the ways
        # remaining_ways = [w for w in range(ways_for_core0, total_ways)]  # Remaining ways for sharing

        # # Create allocation for core 0
        # core0_ways = [w for w in range(0, ways_for_core0)]
        # allocations = [
        #     WayPolicyAllocation(
        #         partition_id=0,
        #         ways=core0_ways
        #     )
        # ]

        # # Create a single shared allocation for all other cores
        # # Each of the other cores (cores 1, 2, and 3) will have the same partition_id (1)
        # # This means they all share the same set of ways
        # allocations.append(
        #     WayPolicyAllocation(
        #         partition_id=1,  # All other cores will use this partition ID
        #         ways=remaining_ways
        #     )
        # )

        # # Create partitioning policy
        # policy = WayPartitioningPolicy(allocations=allocations)

        # # Create partition manager
        # partition_manager = PartitionManager(
        #     partitioning_policies=[policy]
        # )
        ##########################################

        # Define capacity partitioning
        # num_cores = options.num_cpus  # Or however you determine the number of cores
        # partition_ids = []
        # capacities = []

        # # Distribute cache capacity evenly among cores
        # # You can adjust these percentages based on your needs
        # capacity_per_core = 1.0 / num_cores

        # for i in range(num_cores):
        #     partition_ids.append(i)
        #     capacities.append(capacity_per_core)

        # # Create the Max Capacity Partitioning Policy
        # policy = MaxCapacityPartitioningPolicy(
        #     partition_ids=partition_ids,
        #     capacities=capacities
        # )

        # # Create the partition manager
        # partition_manager = PartitionManager(
        #     partitioning_policies=[policy]
        # )
        #####################################################
        # Provide a clock for the L2 and the L1-to-L2 bus here as they
        # are not connected using addTwoLevelCacheHierarchy. Use the
        # same clock as the CPUs.
        system.l2 = l2_cache_class(
            clk_domain=system.cpu_clk_domain, 
            **_get_cache_opts("l2", options)
        )
        # if options.num_cpus > 1:
        #     system.cpu[1].fetch_port = system.l2.cpu_side_fetch

        system.tol2bus = L2XBar(clk_domain=system.cpu_clk_domain)
        system.l2.cpu_side = system.tol2bus.mem_side_ports
        system.l2.mem_side = system.membus.cpu_side_ports

    if options.memchecker:
        system.memchecker = MemChecker()

    for i in range(options.num_cpus):
        if options.caches:
            icache = icache_class(**_get_cache_opts("l1i", options))
            dcache = dcache_class(**_get_cache_opts("l1d", options))

            # If we are using ISA.X86 or ISA.RISCV, we set walker caches.
            if ObjectList.cpu_list.get_isa(options.cpu_type) in [
                ISA.RISCV,
                ISA.X86,
            ]:
                iwalkcache = PageTableWalkerCache()
                dwalkcache = PageTableWalkerCache()
            else:
                iwalkcache = None
                dwalkcache = None

            if options.memchecker:
                dcache_mon = MemCheckerMonitor(warn_only=True)
                dcache_real = dcache

                # Do not pass the memchecker into the constructor of
                # MemCheckerMonitor, as it would create a copy; we require
                # exactly one MemChecker instance.
                dcache_mon.memchecker = system.memchecker

                # Connect monitor
                dcache_mon.mem_side = dcache.cpu_side

                # Let CPU connect to monitors
                dcache = dcache_mon

            # When connecting the caches, the clock is also inherited
            # from the CPU in question
            system.cpu[i].addPrivateSplitL1Caches(
                icache, dcache, iwalkcache, dwalkcache
            )

            if options.memchecker:
                # The mem_side ports of the caches haven't been connected yet.
                # Make sure connectAllPorts connects the right objects.
                system.cpu[i].dcache = dcache_real
                system.cpu[i].dcache_mon = dcache_mon

        elif options.external_memory_system:
            # These port names are presented to whatever 'external' system
            # gem5 is connecting to.  Its configuration will likely depend
            # on these names.  For simplicity, we would advise configuring
            # it to use this naming scheme; if this isn't possible, change
            # the names below.
            if ObjectList.cpu_list.get_isa(options.cpu_type) in [
                ISA.X86,
                ISA.ARM,
                ISA.RISCV,
            ]:
                system.cpu[i].addPrivateSplitL1Caches(
                    ExternalCache("cpu%d.icache" % i),
                    ExternalCache("cpu%d.dcache" % i),
                    ExternalCache("cpu%d.itb_walker_cache" % i),
                    ExternalCache("cpu%d.dtb_walker_cache" % i),
                )
            else:
                system.cpu[i].addPrivateSplitL1Caches(
                    ExternalCache("cpu%d.icache" % i),
                    ExternalCache("cpu%d.dcache" % i),
                )

        system.cpu[i].createInterruptController()
        if options.l2cache:
            bus = i % num_l2caches
            system.cpu[i].connectAllPorts(
                system.tol2bus.cpu_side_ports,
                system.membus.cpu_side_ports,
                system.membus.mem_side_ports,
            )
        elif options.external_memory_system:
            system.cpu[i].connectUncachedPorts(
                system.membus.cpu_side_ports, system.membus.mem_side_ports
            )
        else:
            system.cpu[i].connectBus(system.membus)

    return system


# ExternalSlave provides a "port", but when that port connects to a cache,
# the connecting CPU SimObject wants to refer to its "cpu_side".
# The 'ExternalCache' class provides this adaptation by rewriting the name,
# eliminating distracting changes elsewhere in the config code.
class ExternalCache(ExternalSlave):
    def __getattr__(cls, attr):
        if attr == "cpu_side":
            attr = "port"
        return super(ExternalSlave, cls).__getattr__(attr)

    def __setattr__(cls, attr, value):
        if attr == "cpu_side":
            attr = "port"
        return super(ExternalSlave, cls).__setattr__(attr, value)


def ExternalCacheFactory(port_type):
    def make(name):
        return ExternalCache(
            port_data=name, port_type=port_type, addr_ranges=[AllMemory]
        )

    return make
