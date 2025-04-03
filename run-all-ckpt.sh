#!/bin/bash

# Export root directory for use in all scripts
export GIT_ROOT=$(pwd)

# Common parameters
COMMON_PARAMS="--num-cpus 4 --take-checkpoint"
# Base directory for checkpoints 
CKPT_BASE_DIR="$GIT_ROOT/ckpts-palloc-2bins-320wss"
REQUIRED_CHECKPOINT=3  # We need 3 checkpoint directories

# Define script patterns for read operations
READ_SCRIPTS=(
    # diff read scripts with 1, 2, and 3 attackers
    "diff-1attck-640-read.sh"
    "diff-1attck-1280-read.sh"
    "diff-1attck-1920-read.sh"
    "diff-1attck-2560-read.sh"
    "diff-1attck-3200-read.sh"
    "diff-1attck-5120-read.sh"
    "diff-1attck-320-read.sh"
    "diff-2attck-640-read.sh"
    "diff-2attck-1280-read.sh"
    "diff-2attck-1920-read.sh"
    "diff-2attck-2560-read.sh"
    "diff-2attck-3200-read.sh"
    "diff-2attck-5120-read.sh"
    "diff-2attck-320-read.sh"
    "diff-3attck-640-read.sh"
    "diff-3attck-1280-read.sh"
    "diff-3attck-1920-read.sh"
    "diff-3attck-2560-read.sh"
    "diff-3attck-3200-read.sh"
    "diff-3attck-5120-read.sh"
    "diff-3attck-320-read.sh"
    
    # same read scripts with 1, 2, and 3 attackers
    "same-1attck-640-read.sh"
    "same-1attck-1280-read.sh"
    "same-1attck-1920-read.sh"
    "same-1attck-2560-read.sh"
    "same-1attck-3200-read.sh"
    "same-1attck-5120-read.sh"
    "same-1attck-320-read.sh"
    "same-2attck-640-read.sh"
    "same-2attck-1280-read.sh"
    "same-2attck-1920-read.sh"
    "same-2attck-2560-read.sh"
    "same-2attck-3200-read.sh"
    "same-2attck-5120-read.sh"
    "same-2attck-320-read.sh"
    "same-3attck-640-read.sh"
    "same-3attck-1280-read.sh"
    "same-3attck-1920-read.sh"
    "same-3attck-2560-read.sh"
    "same-3attck-3200-read.sh"
    "same-3attck-5120-read.sh"
    "same-3attck-320-read.sh"

    "same-1attck-640-write.sh"
    "same-1attck-1280-write.sh"
    "same-1attck-1920-write.sh"
    "same-1attck-2560-write.sh"
    "same-1attck-3200-write.sh"
    "same-1attck-5120-write.sh"
    "same-1attck-320-write.sh"
    "same-2attck-640-write.sh"
    "same-2attck-1280-write.sh"
    "same-2attck-1920-write.sh"
    "same-2attck-2560-write.sh"
    "same-2attck-3200-write.sh"
    "same-2attck-5120-write.sh"
    "same-2attck-320-write.sh"
    "same-3attck-640-write.sh"
    "same-3attck-1280-write.sh"
    "same-3attck-1920-write.sh"
    "same-3attck-2560-write.sh"
    "same-3attck-3200-write.sh"
    "same-3attck-5120-write.sh"  
    "same-3attck-320-write.sh"

    "diff-1attck-640-write.sh"
    "diff-1attck-1280-write.sh"
    "diff-1attck-1920-write.sh"
    "diff-1attck-2560-write.sh"
    "diff-1attck-3200-write.sh"
    "diff-1attck-5120-write.sh"
    "diff-1attck-320-write.sh"
    "diff-2attck-640-write.sh"
    "diff-2attck-1280-write.sh"
    "diff-2attck-1920-write.sh"
    "diff-2attck-2560-write.sh"
    "diff-2attck-3200-write.sh"
    "diff-2attck-5120-write.sh"
    "diff-2attck-320-write.sh"
    "diff-3attck-640-write.sh"
    "diff-3attck-1280-write.sh"
    "diff-3attck-1920-write.sh"
    "diff-3attck-2560-write.sh"
    "diff-3attck-3200-write.sh"
    "diff-3attck-5120-write.sh"
    "diff-3attck-320-write.sh"
    
    # same write scripts with 1, 2, and 3 attackers
    "same-1attck-640-write.sh"
    "same-1attck-1280-write.sh"
    "same-1attck-1920-write.sh"
    "same-1attck-2560-write.sh"
    "same-1attck-3200-write.sh"
    "same-1attck-5120-write.sh"
    "same-1attck-320-write.sh"
    "same-2attck-640-write.sh"
    "same-2attck-1280-write.sh"
    "same-2attck-1920-write.sh"
    "same-2attck-2560-write.sh"
    "same-2attck-3200-write.sh"
    "same-2attck-5120-write.sh"
    "same-2attck-320-write.sh"
    "same-3attck-640-write.sh"
    "same-3attck-1280-write.sh"
    "same-3attck-1920-write.sh"
    "same-3attck-2560-write.sh"
    "same-3attck-3200-write.sh"
    "same-3attck-5120-write.sh"
    "same-3attck-320-write.sh"

    "solo-4bank-640-singleBank-read.sh"
    "solo-4bank-1280-singleBank-read.sh"
    "solo-4bank-1920-singleBank-read.sh"
    "solo-4bank-2560-singleBank-read.sh"
    "solo-4bank-3200-singleBank-read.sh"
    "solo-4bank-5120-singleBank-read.sh"
    "solo-4bank-320-singleBank-read.sh"
)

WRITE_SCRIPTS=(
    # diff write scripts with 1, 2, and 3 attackers
    "diff-1attck-640-write.sh"
    "diff-1attck-1280-write.sh"
    "diff-1attck-1920-write.sh"
    "diff-1attck-2560-write.sh"
    "diff-1attck-3200-write.sh"
    "diff-1attck-5120-write.sh"
    "diff-1attck-320-write.sh"
    "diff-2attck-640-write.sh"
    "diff-2attck-1280-write.sh"
    "diff-2attck-1920-write.sh"
    "diff-2attck-2560-write.sh"
    "diff-2attck-3200-write.sh"
    "diff-2attck-5120-write.sh"
    "diff-2attck-320-write.sh"
    "diff-3attck-640-write.sh"
    "diff-3attck-1280-write.sh"
    "diff-3attck-1920-write.sh"
    "diff-3attck-2560-write.sh"
    "diff-3attck-3200-write.sh"
    "diff-3attck-5120-write.sh"
    "diff-3attck-320-write.sh"
    
    # same write scripts with 1, 2, and 3 attackers
    "same-1attck-640-write.sh"
    "same-1attck-1280-write.sh"
    "same-1attck-1920-write.sh"
    "same-1attck-2560-write.sh"
    "same-1attck-3200-write.sh"
    "same-1attck-5120-write.sh"
    "same-1attck-320-write.sh"
    "same-2attck-640-write.sh"
    "same-2attck-1280-write.sh"
    "same-2attck-1920-write.sh"
    "same-2attck-2560-write.sh"
    "same-2attck-3200-write.sh"
    "same-2attck-5120-write.sh"
    "same-2attck-320-write.sh"
    "same-3attck-640-write.sh"
    "same-3attck-1280-write.sh"
    "same-3attck-1920-write.sh"
    "same-3attck-2560-write.sh"
    "same-3attck-3200-write.sh"
    "same-3attck-5120-write.sh"
    "same-3attck-320-write.sh"
)

# Create the checkpoints directory if it doesn't exist
mkdir -p "$CKPT_BASE_DIR"

# Check if ckpt.sh exists and is executable
if [ ! -x "./ckpt.sh" ]; then
    echo "Error: ckpt.sh not found or not executable"
    exit 1
fi

# Function to check if a specific number of checkpoint directories exist
wait_for_checkpoint() {
    local script=$1
    # Determine read or write operation for checkpoint directory naming
    if [[ "$script" == *-read.sh ]]; then
        suffix="read"
    else
        suffix="write"
    fi
    
    local ckpt_dir="$CKPT_BASE_DIR/${script%.sh}"
    
    echo "Waiting for checkpoint #$REQUIRED_CHECKPOINT in $ckpt_dir..."
    
    # Wait for the checkpoint directory to exist
    while [ ! -d "$ckpt_dir" ]; do
        echo "Waiting for checkpoint directory to be created for $script..."
        sleep 10
    done
    
    # Look for the required checkpoint
    local found=false
    while [ "$found" = "false" ]; do
        # Count the checkpoint directories
        local dirs=($(find "$ckpt_dir" -maxdepth 1 -type d -name "cpt.*" | sort))
        local dir_count=${#dirs[@]}
        
        if [ $dir_count -ge $REQUIRED_CHECKPOINT ]; then
            echo "Found $dir_count checkpoint directories. The third checkpoint is: ${dirs[2]}"
            echo "Waiting 60 more seconds to ensure checkpoint is complete..."
            sleep 60  # Wait a bit to ensure the checkpoint is fully written
            found=true
        else
            echo "Found $dir_count checkpoint directories in $ckpt_dir, waiting for at least $REQUIRED_CHECKPOINT..."
            sleep 60
        fi
    done
    
    echo "Checkpoint #$REQUIRED_CHECKPOINT is ready for $script"
    return 0
}

# Function to run simulations for a set of scripts with given latency setting
run_simulations() {
    local scripts=("$@")
    local latency_param=${latency_param:-""}
    
    for script in "${scripts[@]}"; do
        # Extract the number of banks from the script name
        if [[ "$script" =~ -([0-9]+)bank- ]]; then
            num_banks="${BASH_REMATCH[1]}"
            bank_params="--enable-banks --num-banks $num_banks"
        else
            bank_params=""
        fi
        
        # Determine script directory and checkpoint directory based on read or write operation
        if [[ "$script" == *-read.sh ]]; then
            script_dir="guest-scripts-write-palloc"
            ckpt_suffix="read"
        else
            script_dir="guest-scripts-write-palloc"
            ckpt_suffix="write"
        fi
        
        echo "Starting simulation for $script with params: $COMMON_PARAMS $bank_params --script-dir $script_dir --script $script $latency_param"
        
        # Run the script with the appropriate directory
        # Set the checkpoint directory structure properly
        ckpt_dir_param="--checkpoint-dir ${GIT_ROOT}/ckpts-palloc-2bins-320wss/${script%.sh}"
        
        ./ckpt.sh $COMMON_PARAMS $bank_params --script-dir "$script_dir" --script "$script" $ckpt_dir_param $latency_param &
        pid=$!
        echo "Started process with PID: $pid"
        
        # Wait a bit between starting processes to avoid system overload
        sleep 5
    done
}

# Function to periodically count and print the number of gem5.fast processes
count_gem5_processes() {
    while true; do
        count=$(pgrep -c gem5.fast)
        echo "Number of gem5.fast processes running: $count"
        sleep 30
    done
}

# Start the process counter in the background
count_gem5_processes &
COUNTER_PID=$!

# Maximum number of concurrent processes
MAX_CONCURRENT=80

# Function to limit the number of concurrent processes
run_with_concurrency_limit() {
    local scripts=("$@")
    
    for script in "${scripts[@]}"; do
        # Wait until we have fewer than MAX_CONCURRENT processes running
        while [ $(pgrep -c gem5.fast) -ge $MAX_CONCURRENT ]; do
            echo "Currently at max concurrent processes ($(pgrep -c gem5.fast)). Waiting..."
            sleep 30
        done
        
        # Extract the number of banks from the script name
        if [[ "$script" =~ -([0-9]+)bank- ]]; then
            num_banks="${BASH_REMATCH[1]}"
            bank_params="--enable-banks --num-banks $num_banks"
        else
            bank_params=""
        fi
        
        # Determine script directory based on read or write operation
        if [[ "$script" == *-read.sh ]]; then
            script_dir="guest-scripts-write-palloc"
        else
            script_dir="guest-scripts-write-palloc"
        fi
        
        echo "Starting simulation for $script with params: $COMMON_PARAMS $bank_params --script-dir $script_dir --script $script"
        
        # Run the script with the appropriate directory
        ./ckpt.sh $COMMON_PARAMS $bank_params --script-dir "$script_dir" --script "$script" &
        pid=$!
        echo "Started process with PID: $pid"
        
        # Short sleep to allow system to stabilize
        sleep 5
    done
}

# Create a log directory for this run
LOG_DIR="$GIT_ROOT/run_logs/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
echo "Logging to: $LOG_DIR"

# echo "Running read simulations with concurrency limit of $MAX_CONCURRENT..."
# run_with_concurrency_limit "${READ_SCRIPTS[@]}" | tee "$LOG_DIR/read_simulations.log"

# Wait for all read simulations to complete before starting write simulations
# echo "Waiting for all read simulations to complete..."
# wait

echo "Running write simulations with concurrency limit of $MAX_CONCURRENT..."
run_with_concurrency_limit "${READ_SCRIPTS[@]}" | tee "$LOG_DIR/write_simulations.log"

# Wait for all write simulations to complete
echo "Waiting for all write simulations to complete..."
wait

# Kill the counter process
kill $COUNTER_PID

echo "All simulations completed! Logs available in $LOG_DIR"