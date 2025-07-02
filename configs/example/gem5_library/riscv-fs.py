"""
This example runs a simple linux boot with RISC-V.
Modified to support command line arguments for checkpoint usage.

Usage:
    python script.py base-ckpt ckpt              # Create base checkpoint with ATOMIC CPU and DDR4
    python script.py [experiment_name] run       # Run experiment from checkpoint (O3 CPU, memory based on name)
    python script.py [experiment_name] ckpt      # Create experiment checkpoint (ATOMIC CPU, DDR4)
"""

import glob
import math
import os
import sys
from pathlib import Path

from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.cachehierarchies.classic.no_cache import NoCache
from gem5.components.cachehierarchies.classic.private_l1_cache_hierarchy import (
    PrivateL1CacheHierarchy,
)
from gem5.components.cachehierarchies.classic.private_l1_private_l2_walk_cache_hierarchy import (
    PrivateL1PrivateL2WalkCacheHierarchy,
)
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy import (
    PrivateL1SharedL2CacheHierarchy,
)
from gem5.components.memory import (
    SingleChannelDDR3_1600,
    SingleChannelDDR4_2400,
)
from gem5.components.memory.dram_interfaces.hbm import (
    HBM_2000_4H_1x64,
    HBM_2000_4H_1x64_Customized,
    HBM_2000_4H_1x64_New,
)
from gem5.components.memory.hbm import (
    HBM2Stack,
    HighBandwidthMemory,
)
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.linear_generator import LinearGenerator
from gem5.components.processors.linear_generator_core import (
    LinearGeneratorCore,
)
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.traffic_generator import TrafficGenerator
from gem5.isas import ISA
from gem5.resources.resource import (
    BootloaderResource,
    DiskImageResource,
    KernelResource,
    obtain_resource,
)
from gem5.simulate.exit_event import ExitEvent
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires


def extract_mshr_from_experiment_name(experiment_name):
    """Extract MSHR value from experiment name like 'exp1-32mshr-ddr'."""
    import re

    # Pattern to match numbers followed by 'mshr'
    pattern = r"(\d+)mshr"
    match = re.search(pattern, experiment_name)

    if match:
        mshr_value = int(match.group(1))
        print(
            f"Extracted MSHR value: {mshr_value} from experiment: {experiment_name}"
        )
        return mshr_value
    else:
        print(
            f"Warning: Could not extract MSHR value from {experiment_name}, using default"
        )
        return None


def configure_cache_mshrs(cache_hierarchy, experiment_name):
    """Configure cache MSHRs based on experiment name."""
    mshr_value = extract_mshr_from_experiment_name(experiment_name)

    if mshr_value is not None:
        # L1 D-cache mshrs = MSHR value
        l1d_mshrs = mshr_value
        # L2 cache mshrs = 4 * MSHR value
        l2_mshrs = 4 * mshr_value

        print(f"Setting L1 D-cache mshrs to: {l1d_mshrs}")
        print(f"Setting L2 cache mshrs to: {l2_mshrs}")

        # Set L1 D-cache mshrs for all cores
        for i, l1d_cache in enumerate(cache_hierarchy.l1dcaches):
            l1d_cache.mshrs = l1d_mshrs
            l1d_cache.tgts_per_mshr = l1d_tgts
            l1d_cache.write_buffers = l1d_write_buffers
            print(
                f"Set L1 D-cache {i}: mshrs={l1d_mshrs}, tgts_per_mshr={l1d_tgts}, write_buffers={l1d_write_buffers}"
            )

    else:
        # Fallback to default values if MLP extraction fails
        print("Using default mshrs values")
        cache_hierarchy.l2cache.mshrs = 64
        for l1d_cache in cache_hierarchy.l1dcaches:
            l1d_cache.mshrs = 16


def read_script_file(script_path):
    """Read the contents of a script file."""
    try:
        with open(script_path) as file:
            return file.read().strip()
    except FileNotFoundError:
        print(
            f"Warning: Script file {script_path} not found, using fallback command"
        )
        return ""
    except Exception as e:
        print(f"Error reading script file {script_path}: {e}")
        return ""


def find_latest_checkpoint(
    experiment_name, checkpoint_base_dir="/home/gem5/Xperiments"
):
    """Find the latest checkpoint for a given experiment based on tick number."""
    experiment_dir = Path(checkpoint_base_dir) / experiment_name

    if not experiment_dir.exists():
        print(f"Warning: Experiment directory {experiment_dir} does not exist")
        return None

    # Find all checkpoint directories matching pattern cpt.*
    checkpoint_pattern = str(experiment_dir / "cpt.*")
    checkpoint_dirs = glob.glob(checkpoint_pattern)

    if not checkpoint_dirs:
        print(
            f"Warning: No checkpoints found for experiment {experiment_name}"
        )
        return None

    # Extract tick numbers and find the maximum
    max_tick = -1
    latest_checkpoint = None

    for ckpt_dir in checkpoint_dirs:
        ckpt_name = os.path.basename(ckpt_dir)
        if ckpt_name.startswith("cpt."):
            try:
                tick_number = int(ckpt_name[4:])  # Remove "cpt." prefix
                if tick_number > max_tick:
                    max_tick = tick_number
                    latest_checkpoint = ckpt_name
            except ValueError:
                # Skip if tick number is not a valid integer
                print(f"Warning: Invalid checkpoint name format: {ckpt_name}")
                continue

    if latest_checkpoint:
        print(
            f"Found latest checkpoint for {experiment_name}: {latest_checkpoint} (tick: {max_tick})"
        )

    return latest_checkpoint


def checkpoint_exists(
    experiment_name, checkpoint_base_dir="/home/gem5/Xperiments"
):
    """Check if a checkpoint exists for the given experiment."""
    return (
        find_latest_checkpoint(experiment_name, checkpoint_base_dir)
        is not None
    )


def determine_memory_type(experiment_name):
    """Determine memory type based on experiment name."""
    if "hbm" in experiment_name.lower():
        return "hbm"
    elif "ddr" in experiment_name.lower():
        return "ddr"
    else:
        return "ddr"  # Default to DDR


def get_memory_component(memory_type, is_run_mode):
    """Get the appropriate memory component based on type and mode."""
    if is_run_mode:
        # For experiment runs, use memory type based on experiment name
        if memory_type == "hbm":
            return HighBandwidthMemory(
                HBM_2000_4H_1x64_Customized, 8, 128, size="8GiB"
            )
        else:  # ddr
            return SingleChannelDDR4_2400(size="8GiB")
    else:
        # For checkpoint creation, always use DDR4
        return SingleChannelDDR4_2400(size="8GiB")


def get_experiment_command(experiment_name, script_file=None):
    """Get command for experiment, either from script file argument or fallback."""

    # Default fallback command
    default_fallback = (
        'echo "no script has given, exiting the simulation"; m5 exit;'
    )

    # Special case for base-ckpt - no script needed
    if experiment_name == "base-ckpt":
        return ""

    # If script file is provided as argument, try to read it
    if script_file:
        # Check if it's an absolute path or relative path
        if not os.path.isabs(script_file):
            # If relative path, look in the correct script directories
            possible_paths = [
                script_file,  # Current directory
                f"/home/gem5/scripts/{script_file}",  # Correct scripts directory
                f"/home/gem5/{script_file}",  # Base directory
                f"/home/gem5/scripts/{script_file}",  # Alternative location
            ]
        else:
            possible_paths = [script_file]

        # Try each possible path
        for path in possible_paths:
            script_content = read_script_file(path)
            if script_content:
                print(f"Using script file: {path}")
                return script_content

        # If we get here, the script file wasn't found
        print(
            f"Warning: Script file '{script_file}' not found in any of these locations:"
        )
        for path in possible_paths:
            print(f"  - {path}")
        print("Using default fallback command")
        return default_fallback

    # No script file provided - use fallback
    print("No script file provided, using default fallback command")
    return default_fallback


# Experiment mapping - use base command for all experiments
EXPERIMENTS = {
    "test": {"command": "m5 resetstats; bankpll;"},
    "base-ckpt": {"command": ""},
}


# Check command line arguments
if len(sys.argv) < 3 or sys.argv[2] not in ["run", "ckpt"]:
    print("Usage: python script.py [experiment_name] [run|ckpt]")
    print("  experiment_name - one of:", list(EXPERIMENTS.keys()))
    print(
        "  run  - Run experiment from checkpoint (O3 CPU, memory based on experiment name)"
    )
    print("  ckpt - Create checkpoint (ATOMIC CPU, DDR4 memory)")
    print("\nSpecial cases:")
    print("  python script.py base-ckpt ckpt  - Create base checkpoint")
    print(
        "  python script.py [exp_name] run  - Run experiment (creates checkpoint first if needed)"
    )
    sys.exit(1)

# Parse command line arguments
experiment_name = sys.argv[1]
mode = sys.argv[2]

# Parse script file argument (optional for base-ckpt)
script_file = None
if len(sys.argv) > 3:
    script_file = sys.argv[3]
elif experiment_name != "base-ckpt":
    # Script file is required for all experiments except base-ckpt
    print(f"Error: Script file is required for experiment '{experiment_name}'")
    print("Usage: python script.py [experiment_name] [run|ckpt] [script_file]")
    sys.exit(1)
# Run a check to ensure the right version of gem5 is being used.
requires(isa_required=ISA.RISCV)

# Determine configuration based on experiment and mode
if experiment_name == "base-ckpt" and mode == "ckpt":
    # Base checkpoint creation
    print(f"Creating base checkpoint with ATOMIC CPU and DDR4 memory")
    use_checkpoint = False
    cpu_type = CPUTypes.ATOMIC
    memory_type = "ddr"

elif mode == "ckpt":
    # Experiment checkpoint creation - always use ATOMIC CPU and DDR4
    print(
        f"Creating experiment checkpoint for {experiment_name} with ATOMIC CPU and DDR4 memory"
    )
    use_checkpoint = True  # Will load from base-ckpt
    cpu_type = CPUTypes.ATOMIC
    memory_type = "ddr"

elif mode == "run":
    # Check if experiment checkpoint exists
    if checkpoint_exists(experiment_name):
        # Experiment checkpoint exists - run from it with O3 CPU and appropriate memory
        print(f"Experiment checkpoint exists for {experiment_name}")
        use_checkpoint = True
        cpu_type = CPUTypes.O3
        memory_type = determine_memory_type(experiment_name)
        print(f"Using O3 CPU with {memory_type.upper()} memory")
    else:
        # No experiment checkpoint - need to create it first from base-ckpt
        print(f"No checkpoint found for {experiment_name}")
        if not checkpoint_exists("base-ckpt"):
            print(
                "ERROR: Base checkpoint not found. Please run: python script.py base-ckpt ckpt"
            )
            sys.exit(1)
        print(
            f"Creating experiment checkpoint from base-ckpt with ATOMIC CPU and DDR4 memory"
        )
        use_checkpoint = True  # Will load from base-ckpt
        cpu_type = CPUTypes.ATOMIC
        memory_type = "ddr"


# Extract MSHR value for cache configuration
mshr_value = extract_mshr_from_experiment_name(experiment_name)

if mshr_value is not None:
    l1d_mshrs = mshr_value
    l1i_mshrs = mshr_value  # Usually same as L1D
    l2_mshrs = 4 * mshr_value
    # Calculate additional parameters using your scaling formulas
    # l1d_tgts = max(8, l1d_mshrs // 4) # 1:1 ratio, capped at 64
    # l2_tgts = max(12, l2_mshrs // 4)  # More conservative scaling
    # l1d_write_buffers = max(8, l1d_mshrs // 4)  # Capped at 64, minimum 8
    # l2_write_buffers = min(64, max(8, l2_mshrs // 8))

    l1d_tgts = math.ceil(l1d_mshrs * 1.25)
    l2_tgts = math.ceil(l2_mshrs * 0.6)  # More conservative scaling
    l1d_write_buffers = l1d_mshrs / 2
    l2_write_buffers = l2_mshrs / 4

    print(
        f"Configuring caches with L1D mshrs={l1d_mshrs}, L2 mshrs={l2_mshrs}"
    )
    print(f"L1D: tgts={l1d_tgts}, write_buffers={l1d_write_buffers}")
    print(f"L2:  tgts={l2_tgts}, write_buffers={l2_write_buffers}")
else:
    # Default values
    l1d_mshrs = 16
    l1i_mshrs = 16  # Usually same as L1D
    l2_mshrs = 64
    l1d_tgts = 20
    l2_tgts = 38
    l1d_write_buffers = 8
    l2_write_buffers = 20
    print("Using default cache mshrs values")

# Setup the cache hierarchy.
cache_hierarchy = PrivateL1SharedL2CacheHierarchy(
    l1d_size="16KiB",
    l1i_size="16KiB",
    l2_size="32KiB",
    l1d_mshrs=l1d_mshrs,
    l1i_mshrs=l1d_mshrs,  # Usually same as L1D
    l2_mshrs=l2_mshrs,
    l1d_tgts_per_mshr=l1d_tgts,
    l1i_tgts_per_mshr=l1d_tgts,
    l2_tgts_per_mshr=l2_tgts,
    l1d_write_buffers=l1d_write_buffers,
    l2_write_buffers=l2_write_buffers,
)

# cache_hierarchy = PrivateL1CacheHierarchy(
#     l1d_size="16KiB",
#     l1i_size="16KiB",
#     l1d_mshrs=l1d_mshrs,
#     l1i_mshrs=l1i_mshrs,  # Usually same as L1D
#     l1d_tgts_per_mshr=l1d_tgts,
#     l1i_tgts_per_mshr=l1d_tgts  # Usually same as L1D
# )

# cache_hierarchy = NoCache()


# Setup the system memory based on determined type
memory = get_memory_component(
    memory_type, mode == "run" and cpu_type == CPUTypes.O3
)

# Setup a processor with 4 cores and the selected CPU type.
processor = SimpleProcessor(cpu_type=cpu_type, isa=ISA.RISCV, num_cores=4)

if cpu_type == CPUTypes.O3:
    for core in processor.get_cores():
        # Aggressive configuration to increase MLP and outstanding memory requests
        core.core.LQEntries = 96  # Load Queue Entries
        core.core.SQEntries = 96  # Store Queue Entries
        core.core.numIQEntries = 96  # Increase from 192
        core.core.numROBEntries = 384  # Double the ROB size
        # core.core.fetchWidth = 12           # Fetch width
        # core.core.issueWidth = 12           # Issue width
        # core.core.commitWidth = 12          # Commit width
        # core.core.decodeWidth = 12          # Decode width
        # core.core.renameWidth = 12          # Rename width
        # core.core.squashWidth = 12          # Squash width
        # core.core.wbWidth = 12              # Write-back width
        # core.core.dispatchWidth = 12        # Dispatch width
        # core.core.mmu.dtb.size = 8192        # Double data TLB
        # core.core.mmu.itb.size = 512     # 8x larger instruction TLB
        core.core.cacheStorePorts = 400  # Increase store ports
        core.core.cacheLoadPorts = 400  # Increase load ports


# Setup the board.
board = RiscvBoard(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

# Get the command for this experiment using the new function
command = get_experiment_command(experiment_name, script_file)

# Set the Full System workload with or without checkpoint.
kwargs = {
    "kernel": KernelResource(local_path="/home/gem5/resources/vmlinux"),
    "disk_image": DiskImageResource(
        local_path="/home/gem5/resources/connor.img"
    ),
    "bootloader": BootloaderResource(
        local_path="/home/gem5/resources/riscv-bootloader"
    ),
    "readfile_contents": command,
}

# Handle checkpoint loading logic
if use_checkpoint:
    if experiment_name == "base-ckpt":
        # For base-ckpt in ckpt mode, don't load any checkpoint
        print("Creating base checkpoint - no checkpoint to load")
    elif mode == "ckpt" or (
        mode == "run" and not checkpoint_exists(experiment_name)
    ):
        # Load from base-ckpt for experiment checkpoint creation
        base_ckpt = find_latest_checkpoint("base-ckpt")
        if base_ckpt:
            checkpoint_path = Path(
                f"/home/gem5/Xperiments/base-ckpt/{base_ckpt}"
            )
            kwargs["checkpoint"] = checkpoint_path
            print(f"Loading from base checkpoint: {checkpoint_path}")
        else:
            print(
                "ERROR: No base checkpoint found. Please run: python script.py base-ckpt ckpt"
            )
            sys.exit(1)
    else:
        # Load from experiment-specific checkpoint for experiment run
        exp_ckpt = find_latest_checkpoint(experiment_name)
        if exp_ckpt:
            checkpoint_path = Path(
                f"/home/gem5/Xperiments/{experiment_name}/{exp_ckpt}"
            )
            kwargs["checkpoint"] = checkpoint_path
            print(f"Loading from experiment checkpoint: {checkpoint_path}")
        else:
            print(f"ERROR: No checkpoint found for {experiment_name}")
            sys.exit(1)

board.set_kernel_disk_workload(**kwargs)

num_traffic_gens = 1

from m5.objects import PyTrafficGen

# Create traffic generators dynamically based on command line argument
generators = []
for i in range(num_traffic_gens):
    gen_name = f"traffic_gen{i+1}"
    setattr(board, gen_name, PyTrafficGen())
    generators.append(getattr(board, gen_name))
    print(f"Created {gen_name}")

for gen in generators:
    print(f"\n=== Configuring generator {gen} ===")
    print(f"Memory type: {memory_type}")
    print(f"Experiment name: {experiment_name}")

    if memory_type == "hbm":
        if "allBanks" in experiment_name:
            target_bandwidth = 0
        else:  # singleBank
            target_bandwidth = 0
    else:  # DDR
        if "allBanks" in experiment_name:
            target_bandwidth = 0
        else:  # singleBank
            target_bandwidth = 0

    # Use more conservative periods to reduce backpressure
    gen.min_period = 10  # Increased from 100
    gen.max_period = 100  # Increased from 1000
    gen.target_bandwidth = target_bandwidth

    print(f"Set target_bandwidth = {target_bandwidth}")

    if "rdAttk" in experiment_name:
        gen.rd_ratio = 100  # 100% reads for read attack experiments
        print("Configured for READ attack (100% reads)")
    else:
        gen.rd_ratio = 0  # 0% reads = 100% writes for write attack
        print("Configured for WRITE attack (100% writes)")

    if memory_type == "hbm":
        gen.dram_bitmask = 0x78000
        print(f"Set HBM dram_bitmask to: {gen.dram_bitmask}")

        if "singleBank" in experiment_name:
            gen.target_banks = [0]
            gen.target_channels = [1]
            gen.target_pseudo_channels = [1]
            print(
                "HBM singleBank: targeting bank 0, channel 1, pseudo-channel 1"
            )
        else:
            gen.target_banks = []
            gen.target_channels = []
            gen.target_pseudo_channels = []
            print(
                "HBM allBanks: targeting ALL banks, channels, and pseudo-channels"
            )

    elif memory_type == "ddr":
        gen.dram_bitmask = 0x1E000
        print(f"Set DDR dram_bitmask to: {gen.dram_bitmask}")

        if "singleBank" in experiment_name:
            gen.target_banks = [0]
            gen.target_channels = []
            gen.target_pseudo_channels = []
            print(
                "DDR singleBank: targeting bank 0, ALL channels and pseudo-channels"
            )
        else:
            gen.target_banks = []
            gen.target_channels = []
            gen.target_pseudo_channels = []
            print(
                "DDR allBanks: targeting ALL banks, channels, and pseudo-channels"
            )

# Connect to memory bus
cache_hierarchy = board.get_cache_hierarchy()

cache_hierarchy.membus.max_routing_table_size = (
    512  # Set to a higher value for HBM2 stack
)
cache_hierarchy.membus.max_outstanding_snoops = (
    512  # Set to a higher value for HBM2 stack
)
cache_hierarchy.membus.width = 1024  # Set to a higher value for HBM2 stack


for gen in generators:
    gen.port = cache_hierarchy.membus.cpu_side_ports

simulator = Simulator(board=board)

print(f"Beginning simulation for {experiment_name} in {mode} mode!")
print(f"Using {cpu_type} CPU type with {memory_type.upper()} memory")
if use_checkpoint and "checkpoint" in kwargs:
    print(f"Loading checkpoint from: {kwargs['checkpoint']}")
else:
    print("Running from fresh boot")

simulator.run()
