#!/bin/bash

PWD=$(pwd)
# Common parameters
COMMON_PARAMS="--num-cpus 4"
CKPT_BASE_DIR="$PWD/checkpoints/ckpts-palloc-4bins"  # Modified to match your first script's structure
REQUIRED_CHECKPOINT=3  # We need checkpoint #4

# Define script patterns for read operations
READ_SCRIPTS=(
    # # diff read scripts with 1, 2, and 3 attackers
    "diff-1attck-640-read.sh"
    "diff-1attck-1280-read.sh"
    "diff-1attck-1920-read.sh"
    "diff-1attck-2560-read.sh"
    "diff-1attck-3200-read.sh"
    "diff-1attck-5120-read.sh"
    "diff-1attck-10240-read.sh"
    "diff-2attck-640-read.sh"
    "diff-2attck-1280-read.sh"
    "diff-2attck-1920-read.sh"
    "diff-2attck-2560-read.sh"
    "diff-2attck-3200-read.sh"
    "diff-2attck-5120-read.sh"
    "diff-2attck-10240-read.sh"
    "diff-3attck-640-read.sh"
    "diff-3attck-1280-read.sh"
    "diff-3attck-1920-read.sh"
    "diff-3attck-2560-read.sh"
    "diff-3attck-3200-read.sh"
    "diff-3attck-5120-read.sh"
    "diff-3attck-10240-read.sh"
    
    # same read scripts with 1, 2, and 3 attackers
    "same-1attck-640-read.sh"
    "same-1attck-1280-read.sh"
    "same-1attck-1920-read.sh"
    "same-1attck-2560-read.sh"
    "same-1attck-3200-read.sh"
    "same-1attck-5120-read.sh"
    "same-1attck-10240-read.sh"
    "same-2attck-640-read.sh"
    "same-2attck-1280-read.sh"
    "same-2attck-1920-read.sh"
    "same-2attck-2560-read.sh"
    "same-2attck-3200-read.sh"
    "same-2attck-5120-read.sh"
    "same-2attck-10240-read.sh"
    "same-3attck-640-read.sh"
    "same-3attck-1280-read.sh"
    "same-3attck-1920-read.sh"
    "same-3attck-2560-read.sh"
    "same-3attck-3200-read.sh"
    "same-3attck-5120-read.sh"
    "same-3attck-10240-read.sh"


    "same-1attck-640-write.sh"
    "same-1attck-1280-write.sh"
    "same-1attck-1920-write.sh"
    "same-1attck-2560-write.sh"
    "same-1attck-3200-write.sh"
    "same-1attck-5120-write.sh"
    "same-1attck-10240-write.sh"
    "same-2attck-640-write.sh"
    "same-2attck-1280-write.sh"
    "same-2attck-1920-write.sh"
    "same-2attck-2560-write.sh"
    "same-2attck-3200-write.sh"
    "same-2attck-5120-write.sh"
    "same-2attck-10240-write.sh"
    "same-3attck-640-write.sh"
    "same-3attck-1280-write.sh"
    "same-3attck-1920-write.sh"
    "same-3attck-2560-write.sh"
    "same-3attck-3200-write.sh"
    "same-3attck-5120-write.sh"
    "same-3attck-10240-write.sh"

    "diff-1attck-640-write.sh"
    "diff-1attck-1280-write.sh"
    "diff-1attck-1920-write.sh"
    "diff-1attck-2560-write.sh"
    "diff-1attck-3200-write.sh"
    "diff-1attck-5120-write.sh"
    "diff-1attck-10240-write.sh"
    "diff-2attck-640-write.sh"
    "diff-2attck-1280-write.sh"
    "diff-2attck-1920-write.sh"
    "diff-2attck-2560-write.sh"
    "diff-2attck-3200-write.sh"
    "diff-2attck-5120-write.sh"
    "diff-2attck-10240-write.sh"
    "diff-3attck-640-write.sh"
    "diff-3attck-1280-write.sh"
    "diff-3attck-1920-write.sh"
    "diff-3attck-2560-write.sh"
    "diff-3attck-3200-write.sh"
    "diff-3attck-5120-write.sh"
    "diff-3attck-10240-write.sh"

    "solo-4bank-640-singleBank-read.sh"
    "solo-4bank-1280-singleBank-read.sh"
    "solo-4bank-1920-singleBank-read.sh"
    "solo-4bank-2560-singleBank-read.sh"
    "solo-4bank-3200-singleBank-read.sh"
    "solo-4bank-5120-singleBank-read.sh"
    "solo-4bank-10240-singleBank-read.sh"

    "solo-4bank-640-singleBank-write.sh"
    "solo-4bank-1280-singleBank-write.sh"
    "solo-4bank-1920-singleBank-write.sh"
    "solo-4bank-2560-singleBank-write.sh"
    "solo-4bank-3200-singleBank-write.sh"
    "solo-4bank-5120-singleBank-write.sh"
    "solo-4bank-10240-singleBank-write.sh"
)

WRITE_SCRIPTS=(
    # diff write scripts with 1, 2, and 3 attackers
    "diff-1attck-640-write.sh"
    "diff-1attck-1280-write.sh"
    "diff-1attck-1920-write.sh"
    "diff-1attck-2560-write.sh"
    "diff-1attck-3200-write.sh"
    "diff-1attck-5120-write.sh"
    # "diff-1attck-10240-write.sh"
    "diff-2attck-640-write.sh"
    "diff-2attck-1280-write.sh"
    "diff-2attck-1920-write.sh"
    "diff-2attck-2560-write.sh"
    "diff-2attck-3200-write.sh"
    "diff-2attck-5120-write.sh"
    # "diff-2attck-10240-write.sh"
    "diff-3attck-640-write.sh"
    "diff-3attck-1280-write.sh"
    "diff-3attck-1920-write.sh"
    "diff-3attck-2560-write.sh"
    "diff-3attck-3200-write.sh"
    "diff-3attck-5120-write.sh"
    # "diff-3attck-10240-write.sh"
    
    # same write scripts with 1, 2, and 3 attackers
    "same-1attck-640-write.sh"
    "same-1attck-1280-write.sh"
    "same-1attck-1920-write.sh"
    "same-1attck-2560-write.sh"
    "same-1attck-3200-write.sh"
    "same-1attck-5120-write.sh"
    # "same-1attck-10240-write.sh"
    "same-2attck-640-write.sh"
    "same-2attck-1280-write.sh"
    "same-2attck-1920-write.sh"
    "same-2attck-2560-write.sh"
    "same-2attck-3200-write.sh"
    "same-2attck-5120-write.sh"
    # "same-2attck-10240-write.sh"
    "same-3attck-640-write.sh"
    "same-3attck-1280-write.sh"
    "same-3attck-1920-write.sh"
    "same-3attck-2560-write.sh"
    "same-3attck-3200-write.sh"
    "same-3attck-5120-write.sh"
    # "same-3attck-10240-write.sh"
)

# Store which scripts have completed checkpointing
declare -A CHECKPOINT_READY
# Initialize all scripts as not ready
for script in "${READ_SCRIPTS[@]}"; do
    CHECKPOINT_READY["$script"]=false
done

# Function to check if a specific number of checkpoint directories exist
check_checkpoint() {
    local script=$1
    local ckpt_dir="$CKPT_BASE_DIR/${script}"  # Modified to match your first script
    
    echo "Checking for checkpoint #$REQUIRED_CHECKPOINT in $ckpt_dir..."
    
    # Check if the checkpoint directory exists
    if [ ! -d "$ckpt_dir" ]; then
        echo "Checkpoint directory for $script does not exist yet."
        return 1
    fi
    
    # Look for the required checkpoint
    local dirs=($(find "$ckpt_dir" -maxdepth 1 -type d -name "cpt.*" | sort))
    local dir_count=${#dirs[@]}
    
    if [ $dir_count -ge $REQUIRED_CHECKPOINT ]; then
        echo "Found $dir_count checkpoint directories for $script. Required checkpoint is available."
        return 0  # Checkpoint is ready
    else
        echo "Found $dir_count checkpoint directories in $ckpt_dir, need at least $REQUIRED_CHECKPOINT"
        return 1  # Checkpoint is not ready
    fi
}

# Function to check current process count and wait if needed
check_process_count() {
    local current_count=$(pgrep -c gem5.fast)
    if [ $current_count -ge $MAX_PROCESSES ]; then
        echo "Process limit reached: $current_count/$MAX_PROCESSES gem5.fast processes running"
        return 1  # Return failure if at or above limit
    fi
    return 0  # Return success if below limit
}

# Function to run a single simulation
run_single_simulation() {
    local script=$1
    local bank_params=$2
    local mshr_param=$3
    local l2size_param=$4
    
    # Check if we're below process limit
    until check_process_count; do
        echo "Waiting for process count to decrease below $MAX_PROCESSES (currently $(pgrep -c gem5.fast))..."
        sleep 30
    done

    # Determine script directory and checkpoint directory based on read or write operation
    if [[ "$script" == *-read.sh ]]; then
        script_dir="guest-scripts-write-palloc"
        ckpt_suffix="read"
    else
        script_dir="guest-scripts-write-palloc"
        ckpt_suffix="write"
    fi
    sleep 1
    # Now it's safe to launch the simulation
    echo "Starting simulation for $script with params: $COMMON_PARAMS $bank_params --script $script $mshr_param $l2size_param"
    ./run.sh $COMMON_PARAMS $bank_params --script-dir "$script_dir" --script "$script" $mshr_param $l2size_param &
    pid=$!    
    echo "Started process with PID: $pid"
    
    # Brief sleep to allow process to start before next check
    sleep 1
}

# Function to perform round-robin checkpoint checking and run simulations when ready
check_and_run_simulations() {
    local all_ready=false
    
    # Continue checking until all scripts have their checkpoints ready
    while [ "$all_ready" = "false" ]; do
        all_ready=true
        
        # Check each script in round-robin fashion
        for script in "${READ_SCRIPTS[@]}"; do
            # Skip if this script's checkpoint is already confirmed ready
            if [ "${CHECKPOINT_READY["$script"]}" = "true" ]; then
                continue
            fi
            
            # Check if the checkpoint is ready
            if check_checkpoint "$script"; then
                echo "Checkpoint for $script is READY!"
                CHECKPOINT_READY["$script"]=true
                
                # Run simulations for this script with all parameter combinations
                echo "Starting simulations for $script..."
                run_simulations_for_script "$script"
            else
                # This script is not ready, so we're not all ready
                all_ready=false
            fi
            
            # Brief pause before checking next script
            sleep 1
        done
        
        # Wait a bit before next round-robin check if not all ready
        if [ "$all_ready" = "false" ]; then
            echo "Not all checkpoints are ready yet. Waiting 60 seconds before next check..."
            sleep 1
        fi
    done
    
    echo "All script checkpoints are ready and simulations have been launched!"
}

# Function to run all parameter combinations for a single script
run_simulations_for_script() {
    local script=$1
    
    if [[ "$script" =~ -([0-9]+)bank- ]]; then
        num_banks="${BASH_REMATCH[1]}"
        if [ "$num_banks" -eq 2 ]; then
            bank_params="--per-bank-bw 99,99 --enable-banks --num-banks 4"
        else
            bank_params="--per-bank-bw 99,99,99,99 --enable-banks --num-banks 4"
        fi
    else
        bank_params=""
    fi
    
    # Run with various L2 sizes and MSHRs
    echo "Running simulations for $script..."
    for l2size in "${L2_SIZES[@]}"; do
        l2size_param="--l2size $l2size"
        
        for mshr in "${MSHRS[@]}"; do
            mshr_param="--mshrs $mshr"
            run_single_simulation "$script" "$bank_params" "$mshr_param" "$l2size_param"
        done
    done
}

# Function to periodically count and print the number of gem5.fast processes
count_gem5_processes() {
    while true; do
        count=$(pgrep -c gem5.fast)
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Number of gem5.fast processes running: $count"
        sleep 30
    done
}

# Start counting gem5.fast processes in the background
count_gem5_processes &
count_pid=$!
trap "kill $count_pid 2>/dev/null" EXIT

# Define the parameters to test
MSHRS=(256)
L2_SIZES=(2MB)  # L2 cache sizes to sweep

# Maximum allowed concurrent gem5 processes
MAX_PROCESSES=70
echo "Process limit set to $MAX_PROCESSES gem5.fast processes"

# Start the checkpoint checking and simulation process
check_and_run_simulations

echo "All simulations launched! Waiting for remaining processes to complete..."
wait

echo "All simulations completed!"