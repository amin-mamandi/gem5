#!/bin/bash

# Combined Checkpoint Creation and Experiment Runner
# Usage: ./run-sims.sh [auto|checkpoint|run] [debug_mode]
# auto: Automatically create base-ckpt, then experiment checkpoints, then run experiments

MODE=${1:-auto}
DEBUG_MODE=${2:-0}
MAX_PROCESSES=14
CHECKPOINT_BASE_DIR="/home/$USER/simulations"
SCRIPTS_DIR="/home/$USER/guest-scripts"
GEM5_CMD="./build/RISCV/gem5.fast" # use gem5.opt for debugging
SCRIPT="configs/example/gem5_library/riscv-fs.py"

# Validate mode argument
if [[ "$MODE" != "auto" && "$MODE" != "checkpoint" && "$MODE" != "run" ]]; then
    echo "Error: Invalid mode '$MODE'"
    echo "Usage: $0 [auto|checkpoint|run] [debug_mode]"
    echo "  auto:       Create base checkpoint, then experiment checkpoints, then run experiments"
    echo "  checkpoint: Create checkpoints for experiments only"
    echo "  run:        Run experiments from existing checkpoints only"
    echo "  debug_mode: 0 (default) or 1 to enable debug flags"
    exit 1
fi

# Add debug flags if debug mode is enabled
if [ "$DEBUG_MODE" -eq 1 ]; then
    echo "Debug mode enabled"
    GEM5_CMD="$GEM5_CMD --debug-flags=HBM"
else
    echo "Debug mode disabled"
fi

experiment_names=(
   
    "test"
)


# Array to keep track of running processes
declare -A running_processes
declare -A process_experiments

# Function to count currently running gem5.fast processes
count_gem5_processes() {
    pgrep -c "gem5.fast" 2>/dev/null || echo "0"
}

# ==================== BASE CHECKPOINT FUNCTIONS ====================

# Function to check if base checkpoint exists
base_checkpoint_exists() {
    local output_dir="${CHECKPOINT_BASE_DIR}/base-ckpt"
    
    # Check if any checkpoint directory exists
    if ls "$output_dir"/cpt.* 1> /dev/null 2>&1; then
        return 0  # Base checkpoint exists
    else
        return 1  # No base checkpoint found
    fi
}

# Function to check if base checkpoint is complete
base_checkpoint_complete() {
    local output_dir="${CHECKPOINT_BASE_DIR}/base-ckpt"
    
    # Find the checkpoint directory
    local ckpt_dir=$(ls -d "$output_dir"/cpt.* 2>/dev/null | head -1)
    
    if [ -z "$ckpt_dir" ]; then
        return 1  # No checkpoint directory found
    fi
    
    # Check for the actual files that gem5 creates in checkpoints
    if [ -f "$ckpt_dir/m5.cpt" ] && [ -f "$ckpt_dir/board.physmem.store0.pmem" ] && [ -f "$ckpt_dir/board.disk.vio.image.cow" ]; then
        # Additional check: ensure the files are not being written to
        local size1_cpt=$(stat -c%s "$ckpt_dir/m5.cpt" 2>/dev/null || echo "0")
        local size1_pmem=$(stat -c%s "$ckpt_dir/board.physmem.store0.pmem" 2>/dev/null || echo "0")
        
        sleep 3
        
        local size2_cpt=$(stat -c%s "$ckpt_dir/m5.cpt" 2>/dev/null || echo "0")
        local size2_pmem=$(stat -c%s "$ckpt_dir/board.physmem.store0.pmem" 2>/dev/null || echo "0")
        
        # Check if sizes are stable and files are not empty
        if [ "$size1_cpt" -eq "$size2_cpt" ] && [ "$size1_pmem" -eq "$size2_pmem" ] && [ "$size1_cpt" -gt 0 ] && [ "$size1_pmem" -gt 0 ]; then
            return 0  # Checkpoint is complete
        fi
    fi
    
    return 1  # Checkpoint is not complete yet
}

# Function to create base checkpoint
create_base_checkpoint() {
    local output_dir="${CHECKPOINT_BASE_DIR}/base-ckpt"
    
    echo "[$(date)] Creating base checkpoint..."
    
    # Create output directory if it doesn't exist
    mkdir -p "$output_dir"
    
    # Build the command for base checkpoint creation
    local full_cmd="$GEM5_CMD --outdir=$output_dir $SCRIPT base-ckpt ckpt"
    
    echo "  Command: $full_cmd"
    
    # Run the command and wait for completion
    echo "  Starting base checkpoint creation..."
    $full_cmd > "$output_dir/base_checkpoint_creation.log" 2>&1
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ] && base_checkpoint_complete; then
        echo "  ✓ Base checkpoint created successfully"
        return 0
    else
        echo "  ✗ Base checkpoint creation failed (exit code: $exit_code)"
        return 1
    fi
}

# ==================== EXPERIMENT CHECKPOINT FUNCTIONS ====================

# Function to start an experiment checkpoint creation process
start_experiment_checkpoint_process() {
    local exp_name="$1"
    local output_dir="${CHECKPOINT_BASE_DIR}/${exp_name}"
    
    echo "[$(date)] Starting checkpoint creation for: $exp_name"
    
    # Create output directory if it doesn't exist
    mkdir -p "$output_dir"
    
    # Build the command for experiment checkpoint creation
    local full_cmd="$GEM5_CMD --outdir=$output_dir $SCRIPT $exp_name ckpt ${exp_name}.sh"
    
    echo "  Command: $full_cmd"
    
    # Start the process in background and capture PID
    $full_cmd > "$output_dir/checkpoint_creation.log" 2>&1 &
    local pid=$!
    
    # Store the PID and experiment name
    running_processes[$pid]="$exp_name"
    process_experiments["$exp_name"]=$pid
    
    echo "  Started with PID: $pid"
    
    return 0
}

# Function to check if an experiment checkpoint was successfully created
experiment_checkpoint_exists() {
    local exp_name="$1"
    local output_dir="${CHECKPOINT_BASE_DIR}/${exp_name}"
    
    # Check if any checkpoint directory exists
    if ls "$output_dir"/cpt.* 1> /dev/null 2>&1; then
        return 0  # Checkpoint exists
    else
        return 1  # No checkpoint found
    fi
}

# Function to check if experiment checkpoint is complete (has all required files)
experiment_checkpoint_complete() {
    local exp_name="$1"
    local output_dir="${CHECKPOINT_BASE_DIR}/${exp_name}"
    
    # Find the checkpoint directory
    local ckpt_dir=$(ls -d "$output_dir"/cpt.* 2>/dev/null | head -1)
    
    if [ -z "$ckpt_dir" ]; then
        return 1  # No checkpoint directory found
    fi
    
    # Check for the actual files that gem5 creates in checkpoints
    if [ -f "$ckpt_dir/m5.cpt" ] && [ -f "$ckpt_dir/board.physmem.store0.pmem" ] && [ -f "$ckpt_dir/board.disk.vio.image.cow" ]; then
        # Additional check: ensure the files are not being written to
        local size1_cpt=$(stat -c%s "$ckpt_dir/m5.cpt" 2>/dev/null || echo "0")
        local size1_pmem=$(stat -c%s "$ckpt_dir/board.physmem.store0.pmem" 2>/dev/null || echo "0")
        
        sleep 3
        
        local size2_cpt=$(stat -c%s "$ckpt_dir/m5.cpt" 2>/dev/null || echo "0")
        local size2_pmem=$(stat -c%s "$ckpt_dir/board.physmem.store0.pmem" 2>/dev/null || echo "0")
        
        # Check if sizes are stable and files are not empty
        if [ "$size1_cpt" -eq "$size2_cpt" ] && [ "$size1_pmem" -eq "$size2_pmem" ] && [ "$size1_cpt" -gt 0 ] && [ "$size1_pmem" -gt 0 ]; then
            return 0  # Checkpoint is complete
        fi
    fi
    
    return 1  # Checkpoint is not complete yet
}

# Function to monitor experiment checkpoint creation processes
monitor_experiment_checkpoint_processes() {
    local pids_to_remove=()
    
    for pid in "${!running_processes[@]}"; do
        local exp_name="${running_processes[$pid]}"
        
        # Check if process is still running
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "[$(date)] Process $pid ($exp_name) has finished"
            
            # Check if checkpoint was created successfully
            if experiment_checkpoint_complete "$exp_name"; then
                echo "  ✓ Checkpoint created successfully for $exp_name"
            else
                echo "  ✗ Warning: No complete checkpoint found for $exp_name"
            fi
            
            pids_to_remove+=("$pid")
        else
            # Process is still running, check if checkpoint exists
            if experiment_checkpoint_exists "$exp_name"; then
                echo "[$(date)] Checkpoint detected for $exp_name (PID: $pid), waiting for completion..."
                
                # Wait for checkpoint to be complete (always wait full 2 minutes)
                local wait_count=0
                local max_wait=12  # 24 * 5 seconds = 2 minutes
                local checkpoint_confirmed=false
                
                while [ $wait_count -lt $max_wait ]; do
                    # Check if process is still alive while waiting
                    if ! kill -0 "$pid" 2>/dev/null; then
                        echo "  ⚠ Process terminated while waiting for checkpoint completion"
                        checkpoint_confirmed=true
                        break
                    fi
                    
                    if experiment_checkpoint_complete "$exp_name"; then
                        echo "  ✓ Checkpoint files detected, continuing to wait full duration for safety..."
                        checkpoint_confirmed=true
                        # Don't break here - continue waiting the full duration
                    fi
                    
                    echo "  ... waiting for checkpoint to complete ($((wait_count * 6))/120 seconds)"
                    sleep 5
                    ((wait_count++))
                done
                
                # Final check if process is still running before killing
                if kill -0 "$pid" 2>/dev/null; then
                    if [ "$checkpoint_confirmed" = true ]; then
                        echo "  → Full 2-minute wait completed, sending SIGINT to terminate process..."
                    else
                        echo "  → Timeout reached without detecting complete checkpoint, terminating process..."
                    fi
                    
                    # Send SIGINT to gracefully terminate the process
                    kill -2 "$pid" 2>/dev/null
                    
                    # Give it 10 seconds to terminate gracefully
                    local term_wait=0
                    while [ $term_wait -lt 10 ] && kill -0 "$pid" 2>/dev/null; do
                        sleep 1
                        ((term_wait++))
                    done
                    
                    ./Xperiments-allTogether/backup.sh

                    # If still running, force kill
                    if kill -0 "$pid" 2>/dev/null; then
                        echo "  → Process still running, sending SIGKILL..."
                        kill -9 "$pid" 2>/dev/null
                        sleep 2
                    fi
                    
                    echo "  ✓ Terminated process for $exp_name after checkpoint creation"
                else
                    echo "  ✓ Process already terminated for $exp_name"
                fi
                
                pids_to_remove+=("$pid")
            fi
        fi
    done
    
    # Remove finished processes from tracking
    for pid in "${pids_to_remove[@]}"; do
        local exp_name="${running_processes[$pid]}"
        unset running_processes[$pid]
        unset process_experiments["$exp_name"]
    done
}

# ==================== EXPERIMENT RUN FUNCTIONS ====================

# Function to check if experiment already completed successfully
experiment_completed() {
    local exp_name="$1"
    local output_dir="${CHECKPOINT_BASE_DIR}/${exp_name}"
    
    # Check if experiment run log exists and shows completion
    if [ -f "$output_dir/experiment_run.log" ]; then
        # Check if the log indicates the simulation finished (gem5 exit)
        if grep -q "Exiting @ tick" "$output_dir/experiment_run.log" 2>/dev/null; then
            return 0  # Experiment completed successfully
        fi
    fi
    
    return 1  # Experiment not completed yet
}

# Function to start an experiment run
start_experiment_run() {
    local exp_name="$1"
    local output_dir="${CHECKPOINT_BASE_DIR}/${exp_name}"
    # local script_file=$(get_script_file_for_experiment "$exp_name")

    
    echo "[$(date)] Starting experiment run for: $exp_name"
    
    # Build the command (using 'run' mode to load from checkpoint)
    local full_cmd="$GEM5_CMD --outdir=$output_dir $SCRIPT $exp_name run ${exp_name}.sh"
    
    echo "  Command: $full_cmd"
    
    # Start the process in background and capture PID
    $full_cmd > "$output_dir/experiment_run.log" 2>&1 &
    local pid=$!
    
    # Store the PID and experiment name
    running_processes[$pid]="$exp_name"
    process_experiments["$exp_name"]=$pid
    
    echo "  Started with PID: $pid"
    
    return 0
}

# Function to monitor experiment run processes
monitor_experiment_run_processes() {
    local pids_to_remove=()
    
    for pid in "${!running_processes[@]}"; do
        local exp_name="${running_processes[$pid]}"
        
        # Check if process is still running
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "[$(date)] Process $pid ($exp_name) has finished (simulation completed with m5_exit)"
            
            # Since the process terminated naturally, assume it completed successfully
            echo "  ✓ Experiment completed successfully for $exp_name"
            
            pids_to_remove+=("$pid")
        fi
    done
    
    # Remove finished processes from tracking
    for pid in "${pids_to_remove[@]}"; do
        local exp_name="${running_processes[$pid]}"
        unset running_processes[$pid]
        unset process_experiments["$exp_name"]
    done
}

# ==================== COMMON FUNCTIONS ====================

# Function to wait for available slot
wait_for_slot() {
    while [ $(count_gem5_processes) -ge $MAX_PROCESSES ]; do
        echo "[$(date)] Waiting for available slot ($(count_gem5_processes)/$MAX_PROCESSES processes running)..."
        if [ "$1" = "checkpoint" ]; then
            monitor_experiment_checkpoint_processes
        else
            monitor_experiment_run_processes
        fi
        sleep 5
    done
}

# ==================== PHASE FUNCTIONS ====================

# Phase 1: Create base checkpoint
create_base_checkpoint_phase() {
    echo ""
    echo "=== PHASE 1: BASE CHECKPOINT CREATION ==="
    echo ""
    
    if base_checkpoint_complete; then
        echo "[$(date)] Base checkpoint already exists and is complete, skipping creation..."
        return 0
    elif base_checkpoint_exists; then
        echo "[$(date)] Incomplete base checkpoint found, recreating..."
    fi
    
    if create_base_checkpoint; then
        echo "[$(date)] Base checkpoint creation completed successfully!"
        return 0
    else
        echo "[$(date)] Base checkpoint creation failed!"
        return 1
    fi
}

# Phase 2: Create experiment checkpoints
create_experiment_checkpoints_phase() {
    echo ""
    echo "=== PHASE 2: EXPERIMENT CHECKPOINT CREATION ==="
    echo ""
    
    # Process each experiment for checkpoint creation
    for exp_name in "${experiment_names[@]}"; do
        # Check if checkpoint already exists and is complete
        if experiment_checkpoint_complete "$exp_name"; then
            echo "[$(date)] Complete checkpoint already exists for $exp_name, skipping..."
            continue
        elif experiment_checkpoint_exists "$exp_name"; then
            echo "[$(date)] Incomplete checkpoint found for $exp_name, will retry..."
        fi
        
        # Wait for available slot
        wait_for_slot "checkpoint"
        
        # Start the checkpoint process
        if start_experiment_checkpoint_process "$exp_name"; then  
            # Small delay to avoid overwhelming the system
            sleep 2
            
            # Monitor running processes
            monitor_experiment_checkpoint_processes
            
            echo "Currently running: $(count_gem5_processes)/$MAX_PROCESSES processes"
            echo ""
        else
            echo "  ✗ Failed to start checkpoint process for $exp_name"
        fi
    done
    
    # Wait for all remaining processes to complete
    echo "[$(date)] All experiment checkpoint creation started. Waiting for remaining processes to complete..."
    
    while [ ${#running_processes[@]} -gt 0 ]; do
        monitor_experiment_checkpoint_processes
        
        if [ ${#running_processes[@]} -gt 0 ]; then
            echo "[$(date)] Still running: ${#running_processes[@]} processes"
            for pid in "${!running_processes[@]}"; do
                echo "  PID $pid: ${running_processes[$pid]}"
            done
            sleep 10
        fi
    done
    
    echo ""
    echo "[$(date)] All experiment checkpoint creation processes completed!"
    
    # Summary for experiment checkpoint creation
    echo ""
    echo "=== EXPERIMENT CHECKPOINT CREATION SUMMARY ==="
    local completed_count=0
    local failed_count=0
    
    for exp_name in "${experiment_names[@]}"; do
        if experiment_checkpoint_complete "$exp_name"; then
            echo "✓ $exp_name"
            ((completed_count++))
        else
            echo "✗ $exp_name"
            ((failed_count++))
        fi
    done
    
    echo ""
    echo "Completed: $completed_count"
    echo "Failed: $failed_count"
    echo "Total: ${#experiment_names[@]}"
    
    if [ $failed_count -gt 0 ]; then
        echo ""
        echo "Some experiment checkpoints failed. Continuing with available checkpoints..."
        return 1
    else
        echo ""
        echo "All experiment checkpoints created successfully!"
        return 0
    fi
}

# Phase 3: Run experiments
run_experiments_phase() {
    echo ""
    echo "=== PHASE 3: EXPERIMENT EXECUTION ==="
    echo ""
    
    # Process each experiment for running
    for exp_name in "${experiment_names[@]}"; do
        # Check if experiment already completed
        if experiment_completed "$exp_name"; then
            echo "[$(date)] Experiment already completed for $exp_name, skipping..."
            continue
        fi
        
        # Check if checkpoint exists
        if ! experiment_checkpoint_exists "$exp_name"; then
            echo "[$(date)] No checkpoint found for $exp_name, skipping..."
            continue
        fi
        
        # Wait for available slot
        wait_for_slot "run"
        
        # Start the experiment
        start_experiment_run "$exp_name"
        
        # Small delay to avoid overwhelming the system
        sleep 2
        
        # Monitor running processes
        monitor_experiment_run_processes
        
        echo "Currently running: $(count_gem5_processes)/$MAX_PROCESSES processes"
        echo ""
    done
    
    # Wait for all remaining processes to complete
    echo "[$(date)] All experiments started. Waiting for remaining processes to complete..."
    
    while [ ${#running_processes[@]} -gt 0 ]; do
        monitor_experiment_run_processes
        
        if [ ${#running_processes[@]} -gt 0 ]; then
            echo "[$(date)] Still running: ${#running_processes[@]} processes"
            for pid in "${!running_processes[@]}"; do
                echo "  PID $pid: ${running_processes[$pid]}"
            done
            sleep 10
        fi
    done
    
    echo ""
    echo "[$(date)] All experiment runs completed!"
    
    # Final summary for experiment runs
    echo ""
    echo "=== EXPERIMENT RUN SUMMARY ==="
    local completed_count=0
    local failed_count=0
    local no_checkpoint_count=0
    
    for exp_name in "${experiment_names[@]}"; do
        # Check if checkpoint exists
        if ! experiment_checkpoint_exists "$exp_name"; then
            echo "⚠ $exp_name (no checkpoint)"
            ((no_checkpoint_count++))
        elif experiment_completed "$exp_name"; then
            echo "✓ $exp_name (completed)"
            ((completed_count++))
        else
            echo "? $exp_name (ready to run or in progress)"
            ((failed_count++))
        fi
    done
    
    echo ""
    echo "Completed successfully: $completed_count"
    echo "Ready to run or in progress: $failed_count"
    echo "No checkpoint available: $no_checkpoint_count"
    echo "Total: ${#experiment_names[@]}"
    
    return 0
}

# ==================== MAIN EXECUTION ====================

echo "Starting combined manager in $MODE mode"
echo "Scripts directory: $SCRIPTS_DIR"
echo "Maximum concurrent processes: $MAX_PROCESSES"
echo "Total experiments to process: ${#experiment_names[@]}"
echo "Checkpoint base directory: $CHECKPOINT_BASE_DIR"

# Create base checkpoint directory if it doesn't exist
mkdir -p "$CHECKPOINT_BASE_DIR"
mkdir -p "$SCRIPTS_DIR"


if [ "$MODE" = "auto" ]; then
    echo ""
    echo "=== AUTOMATIC FULL PIPELINE MODE ==="
    echo "This will:"
    echo "1. Create base checkpoint (if not exists)"
    echo "2. Create experiment checkpoints for all experiments"
    echo "3. Run all experiments from their checkpoints"
    echo ""
    
    # Phase 1: Create base checkpoint
    if ! create_base_checkpoint_phase; then
        echo "Base checkpoint creation failed. Exiting."
        exit 1
    fi
    
    # Phase 2: Create experiment checkpoints
    create_experiment_checkpoints_phase
    checkpoint_phase_result=$?
    
    # Phase 3: Run experiments (regardless of some checkpoint failures)
    run_experiments_phase
    run_phase_result=$?
    
    echo ""
    echo "=== FINAL SUMMARY ==="
    echo "Base checkpoint: ✓ Created"
    if [ $checkpoint_phase_result -eq 0 ]; then
        echo "Experiment checkpoints: ✓ All successful"
    else
        echo "Experiment checkpoints: ⚠ Some failed"
    fi
    echo "Experiment runs: Completed"
    echo ""
    echo "Full pipeline completed!"
    
elif [ "$MODE" = "checkpoint" ]; then
    echo ""
    echo "=== CHECKPOINT CREATION MODE ==="
    echo ""
    
    # Check if base checkpoint exists
    if ! base_checkpoint_complete; then
        echo "ERROR: Base checkpoint not found or incomplete."
        echo "Please run with 'auto' mode or create base checkpoint first:"
        echo "  $GEM5_CMD --outdir=${CHECKPOINT_BASE_DIR}/base-ckpt $SCRIPT base-ckpt ckpt"
        exit 1
    fi
    
    create_experiment_checkpoints_phase
    exit $?
    
elif [ "$MODE" = "run" ]; then
    echo ""
    echo "=== EXPERIMENT RUN MODE ==="
    echo ""
    
    run_experiments_phase
    exit $?
fi