#!/bin/bash
#SBATCH --job-name=post_process
#SBATCH --output=logs/post_process_%j.log
#SBATCH --error=logs/post_process_%j.err
#SBATCH --mem=2G
#SBATCH --cpus-per-task=1
#SBATCH --time=2:00:00
#SBATCH --partition=ampere
#SBATCH --dependency=afterok:64131

echo 'All gem5 simulations completed successfully!'
echo 'Starting post-processing at: Tue Mar  4 04:19:35 PM CST 2025'

# Add your post-processing commands here
# For example:
# python analyze_results.py

echo 'Post-processing completed at: Tue Mar  4 04:19:35 PM CST 2025'

