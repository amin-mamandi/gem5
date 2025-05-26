#!/bin/bash

# Check if enough arguments are provided
if [ $# -lt 2 ]; then
  echo "Usage: $0 [run|ckpt] [0|1] [additional args...]"
  echo "  First argument: run mode (run or ckpt)"
  echo "  Second argument: debug mode (0=disabled, 1=enabled)"
  echo "  Additional arguments are passed to gem5"
  exit 1
fi

# Parse arguments
MODE=$1
DEBUG_MODE=$2
shift 2  # Remove the first two arguments

# Base command
GEM5_CMD="./build/RISCV/gem5.opt"
SCRIPT="configs/example/gem5_library/riscv-fs.py"

# Add debug flags if debug mode is enabled
if [ "$DEBUG_MODE" -eq 1 ]; then
  echo "Debug mode enabled"
  GEM5_CMD="$GEM5_CMD --debug-flags=PseudoInst,MSHRInst,DetMem,DRAM,MemCtrl,QOS,DRAMState --debug-file=gem5-mshr.debug"
else
  echo "Debug mode disabled"
fi

# Build the final command 
FULL_CMD="$GEM5_CMD $SCRIPT $MODE $@"

echo "Executing: $FULL_CMD"
eval "$FULL_CMD"

# ./m5 enablewaypart 0 &&  taskset -c 0 ./disparity_determ_top --elements 16 --iterations 10 && ./m5 enablewaypart 2 && taskset -c 0 ./disparity_determ_top --elements 128 --iterations 10 && ./m5 cleardm 0 && ./m5 enablewaypart 2 && ./m5 enablememguard 1 && ./m5 setmembudget 0 1000 &&  taskset -c 1 ./disparity_determ_top --elements 16 --iterations 10 && ./m5 cleardm 0 && m5 exit
# taskset -c 0 ./disparity_determ_top --elements 16 --iterations 10 && ./m5 medusa 2 && taskset -c 0 ./disparity_determ_top --elements 16 --iterations 10 && ./m5 enablememguard 1 && ./m5 setmembudget 0 100 &&  taskset -c 1 ./disparity_determ_top --elements 16 --iterations 10 
