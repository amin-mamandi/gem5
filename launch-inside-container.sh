#!/bin/bash

# This script should be run from inside your Charliecloud container
# It handles generating parameters and submitting the jobs

# Create necessary directories
mkdir -p logs
mkdir -p job_outputs
chmod 777 logs job_outputs # Ensure directories are writable

# Generate the parameter combinations
echo "Generating parameter combinations..."
./generate_params.sh

# Count the number of parameter combinations
TOTAL_JOBS=$(wc -l < params.txt)
echo "Total number of jobs to submit: $TOTAL_JOBS"

# Ask for confirmation
read -p "Do you want to submit $TOTAL_JOBS jobs to the SLURM queue? (y/n): " confirm
if [[ "$confirm" != "y" ]]; then
    echo "Aborted."
    exit 0
fi

# Submit the job array
echo "Submitting job array..."
JOBID=$(sbatch --array=1-$TOTAL_JOBS job.sh | awk '{print $4}')

echo "Submitted job array with ID: $JOBID"
echo "To monitor the job status, use: squeue -u $USER"
echo "To cancel all jobs, use: scancel $JOBID"
echo "To view job details, use: sacct -j $JOBID"

echo "Done."
