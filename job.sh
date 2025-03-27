#!/bin/bash

#SBATCH --job-name=gem5_sim
#SBATCH --output=logs/gem5_sim_%A_%a.log
#SBATCH --error=logs/gem5_sim_%A_%a.err
#SBATCH --mem=8G
#SBATCH --cpus-per-task=4
#SBATCH --time=24:00:00
#SBATCH --partition=ampere

# Path to your Charliecloud image
CH_IMAGE="/home/a972m888/ubuntu"
# Working directory inside the container
CONTAINER_WORKDIR="/home/RTAS2025"
# Full path to ch-run command
CH_RUN="/usr/bin/ch-run"  # Update this with the actual full path to ch-run

# Get the command from params.txt file
COMMAND=$(sed "${SLURM_ARRAY_TASK_ID}q;d" params.txt)

# Create a directory for this job's output
JOB_DIR="job_outputs/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
mkdir -p "$JOB_DIR"

# Log the command
echo "Running command: $COMMAND"
echo "Started at: $(date)"

# Execute the command inside Charliecloud container
cd $(dirname "$CH_IMAGE") # Go to the parent directory of your container
$CH_RUN -w "$CH_IMAGE" -- bash -c "cd $CONTAINER_WORKDIR && $COMMAND > $JOB_DIR/simout 2> $JOB_DIR/simerr"

# Check if the command executed successfully
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "Command completed successfully at $(date)"
else
    echo "Command failed with exit code $EXIT_CODE at $(date)"
fi

# Archive any checkpoint directories if they were created
if [ -d "ckpts" ]; then
    echo "Archiving checkpoint directories..."
    tar -czf "$JOB_DIR/checkpoints.tar.gz" ckpts
fi

exit $EXIT_CODE