#!/bin/bash

# This script generates a params.txt file with all parameter combinations
# for your gem5 simulations

# Output file
OUTPUT_FILE="params.txt"
> "$OUTPUT_FILE"  # Clear the file

# Define the parameters to test (from your original script)
BUS_WIDTHS=(32 256 512)
MSHRS=(8 32)
L2_SIZES=("512kB")  # L2 cache sizes to sweep

# Define script patterns
SCRIPTS_5120=(
    "diff-4bank-1core-5120.sh"
    "diff-4bank-3cores-5120.sh"
    "diff-4bank-2cores-5120.sh"
    "same-4bank-1core-5120.sh"
    "same-4bank-3cores-5120.sh"
    "same-4bank-2cores-5120.sh"
    "solo-4bank-5120-singleBank.sh"
    "solo-4bank-5120-allBanks.sh"
)

# Generate all parameter combinations and write to params.txt
for script in "${SCRIPTS_5120[@]}"; do
    # Determine bank params
    if [[ "$script" =~ -([0-9]+)bank- ]]; then
        num_banks="${BASH_REMATCH[1]}"
        if [ "$num_banks" -eq 2 ]; then
            bank_params="--per-bank-bw 99,99 --enable-banks --num-banks $num_banks"
        else
            bank_params="--per-bank-bw 99,99,99,99 --enable-banks --num-banks $num_banks"
        fi
    else
        bank_params=""
    fi

    # First, add combinations with default latency
    for l2size in "${L2_SIZES[@]}"; do
        l2size_param="--l2size $l2size"
        
        for mshr in "${MSHRS[@]}"; do
            mshr_param="--mshrs $mshr"
            
            for width in "${BUS_WIDTHS[@]}"; do
                width_param="--bus-width $width"
                echo "./run.sh --num-cpus 4 $bank_params --script $script $width_param $mshr_param $l2size_param" >> "$OUTPUT_FILE"
            done
        done
    done

    # Then, add combinations with no latency
    for l2size in "${L2_SIZES[@]}"; do
        l2size_param="--l2size $l2size"
        
        for mshr in "${MSHRS[@]}"; do
            mshr_param="--mshrs $mshr"
            
            for width in "${BUS_WIDTHS[@]}"; do
                width_param="--bus-width $width"
                echo "./run.sh --num-cpus 4 $bank_params --script $script --bus-no-latency $width_param $mshr_param $l2size_param" >> "$OUTPUT_FILE"
            done
        done
    done
done

TOTAL_JOBS=$(wc -l < "$OUTPUT_FILE")
echo "Generated $TOTAL_JOBS parameter combinations in $OUTPUT_FILE"
