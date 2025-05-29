"""
This example runs a simple linux boot with RISC-V.
Modified to support command line arguments for checkpoint usage.

Usage:
    python script.py run   # Uses TIMING CPU and loads from checkpoint
    python script.py ckpt  # Uses ATOMIC CPU and doesn't load from checkpoint
"""

import sys
from pathlib import Path

from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.cachehierarchies.classic.private_l1_private_l2_walk_cache_hierarchy import (
    PrivateL1PrivateL2WalkCacheHierarchy,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy import (
    PrivateL1SharedL2CacheHierarchy,
)
from gem5.components.memory import SingleChannelDDR3_1600
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.isas import ISA
from gem5.resources.resource import (
    BootloaderResource,
    DiskImageResource,
    KernelResource,
    obtain_resource,
)
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires

# Check command line arguments
if len(sys.argv) < 2 or sys.argv[1] not in ["run", "ckpt"]:
    print("Usage: python script.py [run|ckpt]")
    print("  run  - Uses TIMING CPU and loads from checkpoint")
    print("  ckpt - Uses ATOMIC CPU and doesn't load from checkpoint")
    sys.exit(1)

# Determine mode based on command line argument
mode = sys.argv[1]
use_checkpoint = mode == "run"
cpu_type = CPUTypes.O3 if use_checkpoint else CPUTypes.ATOMIC

# Run a check to ensure the right version of gem5 is being used.
requires(isa_required=ISA.RISCV)

# Setup the cache hierarchy.
cache_hierarchy = PrivateL1SharedL2CacheHierarchy(
    l1d_size="32KiB", l1i_size="32KiB", l2_size="256KiB"
)

# Setup the system memory.
memory = SingleChannelDDR3_1600()

# Setup a processor with 4 cores and the selected CPU type.
processor = SimpleProcessor(cpu_type=cpu_type, isa=ISA.RISCV, num_cores=4)

# Setup the board.
board = RiscvBoard(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)
command = "./benchmark.sh;"

# Set the Full System workload with or without checkpoint.
kwargs = {
    "kernel": KernelResource(local_path="/home/RTAS2025/resources/vmlinux"),
    "disk_image": DiskImageResource(
        local_path="/home/RTAS2025/resources/connor.img"
    ),
    "bootloader": BootloaderResource(
        local_path="/home/RTAS2025/resources/riscv-bootloader"
    ),
    "readfile_contents": command,
}

# Add checkpoint only if in 'run' mode
if use_checkpoint:
    kwargs["checkpoint"] = Path(
        "/home/RTAS2025/m5out/cpt.1836385040070"
    )  # 4cores = 1734474966489

board.set_kernel_disk_workload(**kwargs)

simulator = Simulator(board=board)
print(
    f"Beginning simulation in {'run (with checkpoint)'
        if use_checkpoint else 'checkpoint creation'} mode!"
)
print(f"Using {cpu_type} CPU type")
simulator.run()
