# Copyright (c) 2022-23 The Regents of the University of California
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

"""
This script further shows an example of booting an ARM based full system Ubuntu
disk image. This simulation boots the disk image using 2 TIMING CPU cores. The
simulation ends when the startup is completed successfully (i.e. when an
`m5_exit instruction is reached on successful boot).

Usage
-----

```
scons build/ARM/gem5.opt -j<NUM_CPUS>
./build/ARM/gem5.opt configs/example/gem5_library/arm-ubuntu-run-with-kvm.py
```

"""

from m5.objects import (
    ArmDefaultRelease,
    VExpress_GEM5_V1,
    VExpress_GEM5_Foundation,
    VExpress_GEM5_V2,
)

from gem5.coherence_protocol import CoherenceProtocol
from gem5.components.boards.arm_board import ArmBoard
from gem5.components.memory import DualChannelDDR4_2400
from gem5.components.processors.cpu_types import (
    CPUTypes,
    get_cpu_type_from_str,
    get_cpu_types_str_set,
)
from gem5.components.processors.simple_switchable_processor import (
    SimpleSwitchableProcessor,
)
from gem5.components.processors.simple_processor import SimpleProcessor

from gem5.isas import ISA
from gem5.resources.resource import obtain_resource
from gem5.simulate.exit_event import ExitEvent
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires
from gem5.components.memory.hbm import HighBandwidthMemory
from gem5.components.memory import SingleChannelDDR4_2400
from gem5.components.memory.dram_interfaces.hbm import (
    HBM_2000_4H_1x64,
)

from gem5.resources.resource import (
    BootloaderResource,
    DiskImageResource,
    KernelResource,
    CheckpointResource,
)

import argparse
import importlib
import glob
import os
import re
import sys
from pathlib import Path

from gem5.resources.resource import Resource

from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import (
    PrivateL1PrivateL2CacheHierarchy,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy import (
    PrivateL1SharedL2CacheHierarchy,
)
from gem5.components.cachehierarchies.classic.no_cache import NoCache


RESOURCE_DIR = "/home/HBM/resources-qemu"
SCRIPT_DIR = "/home/HBM/guest-scripts"
RUNDIR = "/home/HBM/gem5-runs"

parser = argparse.ArgumentParser(
    description="A script to run the ARM simulations."
)

parser.add_argument(
    "-n",
    "--num-cpus",
    type=int,
    required=False,
    default=4,
    help="The number of CPUs.",
)

parser.add_argument(
    "-c",
    "--cpu",
    type=str,
    choices=get_cpu_types_str_set(),
    required=False,
    default="ATOMIC",
    help="The CPU type.",
)

parser.add_argument(
    "-m",
    "--mem-system",
    type=str,
    choices=("no_cache", "classic", "chi", "mesi_two_level", "mi_example"),
    required=True,
    default="classic",
    help="The memory system.",
)

parser.add_argument(
    "-d",
    "--dram-class",
    type=str,
    choices=("ddr", "hbm"),
    required=False,
    default="ddr",
    help=" The memory class to use.",
)

parser.add_argument(
    "--command",
    type=str,
    required=False,
    default="echo \"no command given\"; m5 exit;",
    help="Direct command to run (overrides script file)."
)

parser.add_argument(
    "--checkpoint",
    type=str,
    required=False,
    default=None,
    help="Path to checkpoint file."
)


args = parser.parse_args()


# This runs a check to ensure the gem5 binary is compiled for ARM.
requires(isa_required=ISA.ARM)

if args.mem_system == "no_cache":

    cache_hierarchy = NoCache()

elif args.mem_system == "classic":

    cache_hierarchy = PrivateL1SharedL2CacheHierarchy(
        l1d_size="8KiB", l1i_size="16KiB", l2_size="32KiB"
    )

elif args.mem_system == "chi":
    requires(coherence_protocol_required=CoherenceProtocol.CHI)
    from gem5.components.cachehierarchies.chi.private_l1_cache_hierarchy import (
        PrivateL1CacheHierarchy,
    )

    cache_hierarchy = PrivateL1CacheHierarchy(
        size="16KiB",
        assoc=4,
    )

elif args.mem_system == "mesi_two_level":
    requires(coherence_protocol_required=CoherenceProtocol.MESI_TWO_LEVEL)
    from gem5.components.cachehierarchies.ruby.mesi_two_level_cache_hierarchy import (
        MESITwoLevelCacheHierarchy,
    )

    cache_hierarchy = MESITwoLevelCacheHierarchy(
        l1d_size="8KiB",
        l1d_assoc=2,
        l1i_size="16KiB",
        l1i_assoc=3,
        l2_size="32KiB",
        l2_assoc=16,
        num_l2_banks=4,
    )

elif args.mem_system == "mi_example":
    requires(coherence_protocol_required=CoherenceProtocol.MI_EXAMPLE)
    from gem5.components.cachehierarchies.ruby.mi_example_cache_hierarchy import (
        MIExampleCacheHierarchy,
    )

    cache_hierarchy = MIExampleCacheHierarchy(size="32KiB", assoc=4)
else:
    raise NotImplementedError(
        f"Memory type '{args.mem_system}' is not supported in the boot tests."
    )

# Setup the system memory.
# python_module = "gem5.components.memory"
# memory_class = getattr(importlib.import_module(python_module), args.dram_class)

# if memory_class is HighBandwidthMemory:
#     memory = HighBandwidthMemory(
#         HBM_2000_4H_1x64, 8, 512, size="8GiB"
#     )
# else:
#     memory = memory_class(size="8GiB")

# memory = HighBandwidthMemory(
#         HBM_2000_4H_1x64, 8, 512, size="8GiB"
#     )

if args.dram_class == "hbm":
    memory = HighBandwidthMemory(
        HBM_2000_4H_1x64, 8, 512, size="8GiB"
    )
else:  # DDR (default)
    memory = SingleChannelDDR4_2400(size="8GiB")

cpu_type = get_cpu_type_from_str(args.cpu)


# Here we setup the processor. This is a special switchable processor in which
# a starting core type and a switch core type must be specified. Once a
# configuration is instantiated a user may call `processor.switch()` to switch
# from the starting core types to the switch core types. In this simulation
# we start with KVM cores to simulate the OS boot, then switch to the Timing
# cores for the command we wish to run after boot.
# processor = SimpleSwitchableProcessor(
#     starting_core_type=CPUTypes.KVM,
#     switch_core_type=cpu_type,
#     isa=ISA.ARM,
#     num_cores=args.num_cpus,
# )
processor = SimpleProcessor(
    cpu_type=cpu_type,
    num_cores=args.num_cpus,
    isa=ISA.ARM,
)

# The ArmBoard requires a `release` to be specified. This adds all the
# extensions or features to the system. We are setting this to for_kvm()
# to enable KVM simulation.
# release = ArmDefaultRelease.for_kvm()
release = ArmDefaultRelease()


# The platform sets up the memory ranges of all the on-chip and off-chip
# devices present on the ARM system. ARM KVM only works with VExpress_GEM5_V1
# on the ArmBoard at the moment.
# platform = VExpress_GEM5_V1()
platform = VExpress_GEM5_Foundation()

# Here we setup the board. The ArmBoard allows for Full-System ARM simulations.
board = ArmBoard(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
    release=release,
    platform=platform,
)

command = args.command

checkpoint_resource = None
if args.checkpoint:
    cp = Path(args.checkpoint).expanduser().resolve()
    if not cp.exists():
        raise FileNotFoundError(f"Checkpoint path does not exist: {cp}")
    checkpoint_resource = CheckpointResource(local_path=str(cp))


board.set_kernel_disk_workload(
    # kernel=Resource(
    #     "arm64-linux-kernel-5.4.49",
    #     resource_directory=RESOURCE_DIR,
    # ),
    kernel=KernelResource(local_path=f"{RESOURCE_DIR}/arm64-linux-kernel-5.4.49"),
    disk_image=DiskImageResource(local_path=f"{RESOURCE_DIR}/arm64-ubuntu-focal-server.img"),
    bootloader=BootloaderResource(local_path=f"{RESOURCE_DIR}/boot_foundation.arm64"),
    kernel_args=["console=ttyAMA0", "root=/dev/vda1", "rw"],
    readfile_contents=command,
    checkpoint=checkpoint_resource,
)


def exit_event_handler():
    # Here we switch the CPU type to Timing.
    print("Switching to Timing CPU")
    processor.switch()
    yield False  # gem5 is now running with Timing cores.
    print("Final exit: end simulation")
    yield True


simulator = Simulator(
    board=board,
    # on_exit_event={
    #     # Here we want override the default behavior for the first m5 exit
    #     # exit event.
    #     ExitEvent.EXIT: exit_event_handler()
    # },
)

simulator.run()
