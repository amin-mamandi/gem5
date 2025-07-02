# from gemmini_dev_a.GemminiDevA import GemminiDevA
from pathlib import Path

from m5.objects import (
    GemminiDevA,
    NDPDevA,
)
from m5.util import warn

from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.cachehierarchies.classic.ndp_compatible_cache_hierarchy import (
    NDPCompatibleCacheHierarchy,
)
from gem5.components.memory import (
    DualChannelDDR4_2400,
    SingleChannelDDR4_2400,
)
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

# Check if simulator was compiled for RISCV
requires(isa_required=ISA.RISCV)

warn(
    "This board is only for NDP devices evaluation purposes, and any performance"
    "results obtained with it are only meaningful when compared with other results"
    "obtained with the same board."
)

memory = SingleChannelDDR4_2400(size="3GB")

processor = SimpleProcessor(
    cpu_type=CPUTypes.TIMING, isa=ISA.RISCV, num_cores=1
)

ndp_device = NDPDevA(
    ndp_ctrl=("0x40000000", "0x40001000"),
    ndp_data=("0x40001000", "0x80000000"),
    max_rsze=0x40,
)

# Create Gemmini device with the same parameters as your SE mode
# gemmini_device = GemminiDevA(
#     ndp_ctrl=("0x80000000", "0xc0000000"),  # Same as SE mode
#     ndp_data=("0x80000000", "0xc0000000"),  # Same as SE mode
#     max_rsze=0x40,
#     max_reqs=64,
# )

cache_hierarchy = NDPCompatibleCacheHierarchy(
    l1d_size="16kB",
    l1i_size="16kB",
    l2_size="256kB",
    ndp_device=ndp_device,
)

board = RiscvBoard(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)


command = (
    "echo 'Hello, World!' && "
    "insmod root/ndp/ndp_dev_a/driver/ndp_dev_a.ko && "
    "mknod /dev/ndp_dev_a c 246 0 && "
    "chmod 666 /dev/ndp_dev_a && "
    "cd root/ndp/ndp_dev_a/driver && "
    "./test_driver driver "
)

board.set_kernel_disk_workload(
    kernel=KernelResource(local_path="/home/RTAS2025/resources-accel/vmlinux"),
    kernel_args=[
        "earlyprintk=ttyS0",
        "console=ttyS0",
        "root=/dev/vda1",
        "rw",
        "mem=2G",
        "memmap=2G@0",
        "memmap=1G$2G",
    ],
    disk_image=DiskImageResource(
        local_path="/home/RTAS2025/resources-accel/connor.img"
    ),
    bootloader=BootloaderResource(
        local_path="/home/RTAS2025/resources-accel/riscv-bootloader"
    ),
    readfile_contents=command,
    # checkpoint=Path("/home/RTAS2025/m5out/cpt.327300603435"),
)


simulator = Simulator(board=board)
simulator.run()
