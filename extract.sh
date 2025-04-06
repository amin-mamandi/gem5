#!/bin/bash

# Create output CSV file with header
echo "directory,bandwidth_MBps,l2_missrate" > results.csv

# For each directory that matches your naming pattern
for dir in diff-*-palloc-4bins same-*-palloc-4bins solo-*-palloc-4bins; do
  # Check if directory exists and contains required files
  if [ -d "$dir" ] && [ -f "$dir/system.terminal" ] && [ -f "$dir/stats.txt" ]; then
    # Try to extract bandwidth from system.terminal file
    bandwidth=$(grep -o "bandwidth [0-9]*\.[0-9]* MB/s" "$dir/system.terminal" | awk '{print $2}')
    
    # If bandwidth not found, calculate it from the data
    if [ -z "$bandwidth" ]; then
      # Extract naccess and elapsed_ns
      naccess=$(grep -o "naccess: [0-9]*" "$dir/system.terminal" | awk '{print $2}')
      elapsed_ns=$(grep -o "elapsed ns: [0-9]*" "$dir/system.terminal" | awk '{print $3}')
      
      # Calculate bandwidth if both values are available
      if [ -n "$naccess" ] && [ -n "$elapsed_ns" ]; then
        # Formula: bandwidth = (64*1000*naccess)/elapsed_ns
        bandwidth=$(echo "scale=2; (64*1000*$naccess)/$elapsed_ns" | bc)
        echo "Calculated bandwidth for $dir: $bandwidth MB/s"
      else
        bandwidth="0"
        echo "Could not calculate bandwidth for $dir (missing data)"
      fi
    fi
    
    # Extract L2 miss rate from stats.txt file
    missrate=$(grep "system.l2.overallMissRate::cpu0.data    " "$dir/stats.txt" | awk '{print $2}')
    
    # If missrate is missing, add placeholder
    if [ -z "$missrate" ]; then
      missrate="0"
    fi
    
    # Append results to CSV
    echo "$dir,$bandwidth,$missrate" >> results.csv
    
    # Print progress
    echo "Processed: $dir"
  fi
done

echo "Extraction complete. Results saved to results.csv"
python3 plot.py