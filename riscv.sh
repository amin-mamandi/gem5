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
  GEM5_CMD="$GEM5_CMD --debug-flags=DetMSHR,PseudoInst,MemGuard,MSHRInst,DetCache,DetMem --debug-file=gem5-10.debug"
else
  echo "Debug mode disabled"
fi

# Build the final command
FULL_CMD="$GEM5_CMD $SCRIPT $MODE $@"

echo "Executing: $FULL_CMD"
eval "$FULL_CMD"

# ./m5 setmembudget 0 100 && ./m5 medusa 2 && ./m5 enablememguard 1 && ./m5 enablewaypart 2 &&  taskset -c 0 ./disparity_determ_top --elements 1024 --iterations 10 && ./m5 enablewaypart 2 && taskset -c 0 ./disparity_determ_top --elements 128 --iterations 10 && ./m5 cleardm 0 && ./m5 enablewaypart 2 && ./m5 enablememguard 1 && ./m5 setmembudget 0 1000 &&  taskset -c 1 ./disparity_determ_top --elements 16 --iterations 10 && ./m5 cleardm 0 && m5 exit
# taskset -c 0 ./disparity_determ_top --elements 16 --iterations 10 && ./m5 medusa 2 && taskset -c 0 ./disparity_determ_top --elements 16 --iterations 10 && ./m5 enablememguard 1 && ./m5 setmembudget 0 100 &&  taskset -c 1 ./disparity_determ_top --elements 16 --iterations 10



# ./disparity_determ_top -m 1024 -l 8 -i 100 -c 0  =>  BW: 806.77 MB/s

# ./disparity_determ_top -m 1024 -l 8 -i 100 -c 0 -G 1 -B 100 =>  BW: 807.01 MB/s

# ./disparity_determ_top -m 1024 -l 8 -i 100 -c 0 -G 1 -B 1000 =>  BW:

# ./disparity_determ_top -m 1024 -l 8 -i 100 -c 0 -M 3 =>  BW:

# ./disparity_determ_top -m 1024 -l 8 -i 100 -c 0 -M 3 -W 2 =>  BW: 806.64 MB/s

# ./disparity_determ_top -m 1024 -l 8 -i 100 -c 0 -M 3 -W 2 -G 1 -B 100 =>  BW:

# ./disparity_determ_top -m 10240 -l 8 -i 1 -c 0 -W 2 -G 1 -B 100 -C && m5 exit   =>  BW:


# ./disparity_determ_top -m 1024 -l 8 -i 1 -c 0 -W 2 -G 1 -B 10 -C && m5 exit   =>  BW:








# Is equivalent to this sequence:
# (after restoring checkpoint)
# ./m5 medusa 3
# ./m5 enablewaypart 2
# ./m5 enablememguard 1
# ./m5 setmembudget 0 100
# taskset -c 0 ./mlp -m 256 -l 1 -i 10000 -x
# ./m5 cleardm 0


# Basic run with Medusa level 3, way partitioning, memguard, and memory budget
# ./mlp -m 256 -l 1 -i 10000 -x -M 3 -W 2 -G 1 -B 100 -C

# Different MLP levels with security
# ./mlp -m 256 -l 4 -i 5000 -x -M 2 -W 2 -G 1 -B 500 -C

# CPU affinity with security features
# ./mlp -m 512 -l 2 -i 8000 -c 0 -x -M 3 -W 1 -G 1 -B 200 -C
