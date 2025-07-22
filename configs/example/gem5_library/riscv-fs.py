# Copyright (c) 2021 The Regents of the University of California
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
This example runs a simple linux boot. It uses the 'riscv-disk-img' resource.
It is built with the sources in `src/riscv-fs` in [gem5 resources](
https://github.com/gem5/gem5-resources).

Characteristics
---------------

* Runs exclusively on the RISC-V ISA with the classic caches
* Assumes that the kernel is compiled into the bootloader
* Automatically generates the DTB file
* Will boot but requires a user to login using `m5term` (username: `root`,
  password: `root`)
"""

import sys
import m5
import os
import glob
from pathlib import Path

from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.cachehierarchies.classic.private_l1_private_l2_walk_cache_hierarchy import (
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
)
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires


def read_script_file(script_path):
    """Read the contents of a script file."""
    try:
        with open(script_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Warning: Script file {script_path} not found, using fallback command")
        return ""
    except Exception as e:
        print(f"Error reading script file {script_path}: {e}")
        return ""



def find_latest_checkpoint(experiment_name, checkpoint_base_dir="/home/$USER/simulations"):
    """Find the latest checkpoint for a given experiment based on tick number."""
    experiment_dir = Path(checkpoint_base_dir) / experiment_name
    
    if not experiment_dir.exists():
        print(f"Warning: Experiment directory {experiment_dir} does not exist")
        return None
    
    # Find all checkpoint directories matching pattern cpt.*
    checkpoint_pattern = str(experiment_dir / "cpt.*")
    checkpoint_dirs = glob.glob(checkpoint_pattern)
    
    if not checkpoint_dirs:
        print(f"Warning: No checkpoints found for experiment {experiment_name}")
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
        print(f"Found latest checkpoint for {experiment_name}: {latest_checkpoint} (tick: {max_tick})")
    
    return latest_checkpoint


def checkpoint_exists(experiment_name, checkpoint_base_dir="/home/$USER/simulations"):
    """Check if a checkpoint exists for the given experiment."""
    return find_latest_checkpoint(experiment_name, checkpoint_base_dir) is not None


def get_experiment_command(experiment_name, script_file=None):
    """Get command for experiment, either from script file argument or fallback."""
    
    # Default fallback command
    default_fallback = 'echo "no script has given, exiting the simulation"; m5 exit;'
    
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
                f"/home/RTAS2025/scripts-sweep/{script_file}",  # Correct scripts directory
                f"/home/RTAS2025/{script_file}",  # Base directory
                f"/home/RTAS2025/scripts-sweep/{script_file}",  # Alternative location
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
        print(f"Warning: Script file '{script_file}' not found in any of these locations:")
        for path in possible_paths:
            print(f"  - {path}")
        print("Using default fallback command")
        return default_fallback
    
    # No script file provided - use fallback
    print("No script file provided, using default fallback command")
    return default_fallback

# Check command line arguments
if len(sys.argv) < 3 or sys.argv[2] not in ["run", "ckpt"]:
    print("Usage: riscv-fs.py [experiment_name] [run|ckpt]")
    print("  run  - Run experiment from checkpoint (O3 CPU, memory based on experiment name)")
    print("  ckpt - Create checkpoint (ATOMIC CPU)")
    print("  python script.py base-ckpt ckpt  - Create base checkpoint")
    print("  python script.py [exp_name] run  - Run experiment (creates checkpoint first if needed)")
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
    print(f"Creating base checkpoint with ATOMIC CPU")
    use_checkpoint = False
    cpu_type = CPUTypes.ATOMIC
elif mode == "ckpt":
    # Experiment checkpoint creation - always use ATOMIC CPU and DDR4
    print(f"Creating experiment checkpoint for {experiment_name} with ATOMIC CPU")
    use_checkpoint = True  # Will load from base-ckpt
    cpu_type = CPUTypes.ATOMIC
    
elif mode == "run":
    # Check if experiment checkpoint exists
    if checkpoint_exists(experiment_name):
        # Experiment checkpoint exists - run from it with O3 CPU
        print(f"Experiment checkpoint exists for {experiment_name}")
        use_checkpoint = True
        cpu_type = CPUTypes.O3
    else:
        # No experiment checkpoint - need to create it first from base-ckpt
        print(f"No checkpoint found for {experiment_name}")
        if not checkpoint_exists("base-ckpt"):
            print("ERROR: Base checkpoint not found. Please run: python script.py base-ckpt ckpt")
            sys.exit(1)
        print(f"Creating experiment checkpoint from base-ckpt with ATOMIC CPU")
        use_checkpoint = True  # Will load from base-ckpt
        cpu_type = CPUTypes.ATOMIC

# Run a check to ensure the right version of gem5 is being used.
requires(isa_required=ISA.RISCV)

# Setup the cache hierarchy.
# For classic, PrivateL1PrivateL2 and NoCache have been tested.
# For Ruby, MESI_Two_Level and MI_example have been tested.
cache_hierarchy = PrivateL1SharedL2CacheHierarchy(
    l1d_size="32KiB", l1i_size="32KiB", l2_size="512KiB"
)

# Setup the system memory.
memory = SingleChannelDDR3_1600()

# Setup a single core Processor.
processor = SimpleProcessor(
    cpu_type=cpu_type, isa=ISA.RISCV, num_cores=1
)

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
    "kernel": KernelResource(local_path="/home/$USER/gem5-fs-resources/vmlinux"),
    "disk_image": DiskImageResource(
        local_path="/home/$USER/gem5-fs-resources/diskImage"
    ),
    "bootloader": BootloaderResource(
        local_path="/home/$USER/gem5-fs-resources/riscv-bootloader"
    ),
    "readfile_contents": command,
}

# Handle checkpoint loading logic
if use_checkpoint:
    if experiment_name == "base-ckpt":
        # For base-ckpt in ckpt mode, don't load any checkpoint
        print("Creating base checkpoint - no checkpoint to load")
    elif mode == "ckpt" or (mode == "run" and not checkpoint_exists(experiment_name)):
        # Load from base-ckpt for experiment checkpoint creation
        base_ckpt = find_latest_checkpoint("base-ckpt")
        if base_ckpt:
            checkpoint_path = Path(f"/home/$USER/simulations/base-ckpt/{base_ckpt}")
            kwargs["checkpoint"] = checkpoint_path
            print(f"Loading from base checkpoint: {checkpoint_path}")
        else:
            print("ERROR: No base checkpoint found. Please run: python script.py base-ckpt ckpt")
            sys.exit(1)
    else:
        # Load from experiment-specific checkpoint for experiment run
        exp_ckpt = find_latest_checkpoint(experiment_name)
        if exp_ckpt:
            checkpoint_path = Path(f"/home/$USER/simulations/{experiment_name}/{exp_ckpt}")
            kwargs["checkpoint"] = checkpoint_path
            print(f"Loading from experiment checkpoint: {checkpoint_path}")
        else:
            print(f"ERROR: No checkpoint found for {experiment_name}")
            sys.exit(1)

board.set_kernel_disk_workload(**kwargs)


simulator = Simulator(board=board)
print("Beginning simulation!")
# Note: This simulation will never stop. You can access the terminal upon boot
# using m5term (`./util/term`): `./m5term localhost <port>`. Note the `<port>`
# value is obtained from the gem5 terminal stdout. Look out for
# "system.platform.terminal: Listening for connections on port <port>".
simulator.run()
