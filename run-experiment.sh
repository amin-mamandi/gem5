#!/bin/bash

# Path to your Charliecloud image
CH_IMAGE="/home/a972m888/ubuntu"
# Working directory inside the container
CONTAINER_WORKDIR="/home/RTAS2025"

# Create necessary directories
mkdir -p logs
mkdir -p job_outputs
chmod 777 logs job_outputs # Ensure directories are writable from within container

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

# Optional: Submit a dependency job for post-processing
read -p "Do you want to submit a post-processing job that will run after all simulations complete? (y/n): " post_confirm
if [[ "$post_confirm" == "y" ]]; then
    echo "#!/bin/bash
#SBATCH --job-name=post_process
#SBATCH --output=logs/post_process_%j.log
#SBATCH --error=logs/post_process_%j.err
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1
#SBATCH --time=2:00:00
#SBATCH --partition=ampere
#SBATCH --dependency=afterok:$JOBID

echo 'All gem5 simulations completed successfully!'
echo 'Starting post-processing at: $(date)'

# Add your post-processing commands here
# For example:
# python analyze_results.py

echo 'Post-processing completed at: $(date)'
" > post_process.sh

    chmod +x post_process.sh
    POST_JOBID=$(sbatch post_process.sh | awk '{print $4}')
    echo "Submitted post-processing job with ID: $POST_JOBID"
fi

echo "Done."