#!/bin/bash

# Root directories
export GIT_ROOT=$(pwd)
GEM5_DIR=${GIT_ROOT}/gem5
GUEST_SCRIPT_DIR=${GIT_ROOT}/guest-scripts
RESOURCES=${GIT_ROOT}/resources-sync
RUNDIR_BASE="${GIT_ROOT}/rundir"

# Default parameters based on ARM Cortex-A72
num_threads=1
num_cpus=4
Freq="2GHz"  # Typical A72 frequency
GUEST_SCRIPT="same-bank.sh"
RESTORE=2

# Memory hierarchy parameters (A72 typical configs)
L1D_SIZE="32kB"
L1I_SIZE="64kB"
L2_SIZE="8MB"
L1D_ASSOC=2
L1I_ASSOC=3
L2_ASSOC=16

# Bank and bandwidth regulation parameters
ENABLE_BANKS="False"
ENABLE_BW_REGULATION="False"
NUM_BANKS=4
MONITOR_WINDOW=100000000000
declare -a BANK_BWS_MB  # Bandwidths in MB/s as input
declare -a BANK_BWS    # Converted to bytes/s for gem5

# Function to convert MB/s to bytes/s
function mbs_to_bytes() {
    echo $(( $1 * 1000000 ))
}

# Cortex-A72 core parameters
INT_REGS=128
FLOAT_REGS=128
VEC_REGS=128
ROB_ENTRIES=128
BTB_SIZE=4096
DTB_SIZE=32
ITB_SIZE=48
IQ_SIZE=44  # A72 spec
LQ_SIZE=64  # A72 spec
SQ_SIZE=36  # A72 spec

# Pipeline width parameters (A72 is 5-wide)
WIDTH=3
FETCH_WIDTH=$WIDTH
DECODE_WIDTH=$WIDTH
RENAME_WIDTH=$WIDTH
ISSUE_WIDTH=$WIDTH
WB_WIDTH=$WIDTH
DISPATCH_WIDTH=$WIDTH
COMMIT_WIDTH=$WIDTH
SQUASH_WIDTH=$WIDTH

# Cache configuration
CACHE_CONFIG="
    --caches
    --l2cache
    --cacheline_size=64
    --l1d_size=$L1D_SIZE
    --l1i_size=$L1I_SIZE
    --l2_assoc=$L2_ASSOC
"

CPU_CONFIG="
    --param=system.cpu[:].numPhysFloatRegs=$FLOAT_REGS
    --param=system.cpu[:].numPhysIntRegs=$INT_REGS
    --param=system.cpu[:].numPhysVecRegs=$VEC_REGS
    --param=system.cpu[:].numPhysVecPredRegs=32
    --param=system.cpu[:].numPhysMatRegs=32
    --param=system.cpu[:].numROBEntries=$ROB_ENTRIES
    --param=system.cpu[:].numIQEntries=$IQ_SIZE
    --param=system.cpu[:].LQEntries=$LQ_SIZE
    --param=system.cpu[:].SQEntries=$SQ_SIZE
    --param=system.cpu[:].branchPred.btb.numEntries=$BTB_SIZE
    --param=system.cpu[:].mmu.dtb.size=$DTB_SIZE
    --param=system.cpu[:].mmu.itb.size=$ITB_SIZE
    --param=system.cpu[:].fetchWidth=$FETCH_WIDTH
    --param=system.cpu[:].decodeWidth=$DECODE_WIDTH
    --param=system.cpu[:].renameWidth=$RENAME_WIDTH
    --param=system.cpu[:].issueWidth=$ISSUE_WIDTH
    --param=system.cpu[:].wbWidth=$WB_WIDTH
    --param=system.cpu[:].dispatchWidth=$DISPATCH_WIDTH
    --param=system.cpu[:].commitWidth=$COMMIT_WIDTH
    "

# And add a separate configuration for the O3 CPU parameters
O3_CONFIG="
    --param system.switch_cpus[:].LQEntries=$LQ_SIZE
    --param system.switch_cpus[:].SQEntries=$SQ_SIZE
    --param system.switch_cpus[:].numROBEntries=$ROB_ENTRIES
    --param system.switch_cpus[:].numIQEntries=$IQ_SIZE
    --param system.switch_cpus[:].numPhysIntRegs=$INT_REGS
    --param system.switch_cpus[:].numPhysFloatRegs=$FLOAT_REGS
    --param system.switch_cpus[:].numPhysVecRegs=$VEC_REGS
    --param system.switch_cpus[:].numPhysVecPredRegs=32
    --param system.switch_cpus[:].numPhysMatRegs=32
    --param system.switch_cpus[:].mmu.dtb.size=$DTB_SIZE
    --param system.switch_cpus[:].mmu.itb.size=$ITB_SIZE
    --param system.switch_cpus[:].fetchWidth=$FETCH_WIDTH
    --param system.switch_cpus[:].decodeWidth=$DECODE_WIDTH
    --param system.switch_cpus[:].renameWidth=$RENAME_WIDTH
    --param system.switch_cpus[:].issueWidth=$ISSUE_WIDTH
    --param system.switch_cpus[:].wbWidth=$WB_WIDTH
    --param system.switch_cpus[:].dispatchWidth=$DISPATCH_WIDTH
    --param system.switch_cpus[:].commitWidth=$COMMIT_WIDTH
"

function usage {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --num-cpus N            Number of CPU cores"
    echo "  --num-threads N         Number of threads"
    echo "  --freq FREQ            CPU frequency"
    echo "  --enable-banks         Enable bank support"
    echo "  --enable-bw-regulation Enable bandwidth regulation"
    echo "  --num-banks N          Number of banks"
    echo "  --per-bank-bw LIST     Comma-separated list of bandwidths"
    echo "  --monitor-window N     Monitor window size"
    echo "  --take-checkpoint      Take checkpoint"
    echo "  --help                 Show this help message"
    exit 1
}

# Parse command line arguments
TEMP=$(getopt -o 'h' --long num-cpus:,num-threads:,restore:,script-dir:,freq:,l2size:,mshrs:,name:,enable-banks,enable-bw-regulation,num-banks:,per-bank-bw:,monitor-window:,script:,take-checkpoint,help -n 'run-simulation.sh' -- "$@")

eval set -- "$TEMP"

while true; do
    case "$1" in
        --num-threads) num_threads="$2"; shift 2 ;;
        --num-cpus) num_cpus="$2"; shift 2 ;;
        --freq) Freq="$2"; shift 2 ;;
        --enable-banks) ENABLE_BANKS="True"; shift 1 ;;
        --enable-bw-regulation) ENABLE_BW_REGULATION="True"; shift 1 ;;
        --num-banks) NUM_BANKS="$2"; shift 2 ;;
        --per-bank-bw) IFS=',' read -ra BANK_BWS_MB <<< "$2"; 
                     # Convert MB/s to bytes/s
                     for bw in "${BANK_BWS_MB[@]}"; do
                         BANK_BWS+=($(mbs_to_bytes $bw))
                     done
                     shift 2 ;;
        --monitor-window) MONITOR_WINDOW="$2"; shift 2 ;;
        --script) GUEST_SCRIPT="$2"; shift 2 ;;
        --take-checkpoint) checkpoint=1; shift 1 ;;
        --name) name="$2"; shift 2 ;;
        --mshrs) MSHRS="$2"; shift 2 ;;
        --l2size) L2_SIZE="$2"; shift 2 ;;
        --restore) RESTORE="$2"; shift 2 ;;
        --script-dir ) GUEST_SCRIPT_DIR="$2" ; shift 2 ;;
        -h | --help) usage ;;
        --) shift; break ;;
        *) break ;;
    esac
done

CKPT_DIR=${GIT_ROOT}/ckpts-sync-3/$GUEST_SCRIPT
RUNDIR=""

function setup_dirs {
    mkdir -p "$CKPT_DIR"
    mkdir -p "$RUNDIR"
    # Create parent directories for the simout file to ensure redirection works
    mkdir -p "$(dirname "$RUNDIR/simout")"
}

# Setup RUNDIR based on parameters outside of run_simulation
if [[ -n "$checkpoint" ]]; then
    RUNDIR=${GIT_ROOT}/ckptDir/$GUEST_SCRIPT-sync-3
else
    # Create descriptive directory name including bank configs
    BANK_INFO=""
    if [ "$ENABLE_BANKS" = "True" ]; then
        if [ ${#BANK_BWS_MB[@]} -eq $NUM_BANKS ]; then
            # Use the original MB/s values for directory name
            BANK_INFO="${NUM_BANKS}banks"$(IFS=_; echo "${BANK_BWS_MB[*]}")"MB"
        else
            BANK_INFO="${NUM_BANKS}banks-default"
        fi
    fi

    # Add L2 size to directory name
    L2_SIZE_INFO="-l2size${L2_SIZE}"
    
    # Add MSHRS info if specified
    if [[ -n "$MSHRS" ]]; then
        MSHR_INFO="-l2mshrs${MSHRS}"
    else
        MSHR_INFO=""
    fi
    
    RUNDIR=${GIT_ROOT}/runDir-3/$GUEST_SCRIPT-sync-PartID-debug-int0
fi

function run_simulation {
    if [ ${#BANK_BWS[@]} -gt 0 ] && [ ${#BANK_BWS[@]} -ne $NUM_BANKS ]; then
        echo "Error: Number of bandwidth values (${#BANK_BWS[@]}) does not match number of banks ($NUM_BANKS)"
        exit 1
    fi

    # Set up bandwidth configuration
    BW_CONFIG=""
    if [ ${#BANK_BWS[@]} -eq $NUM_BANKS ]; then
        BW_LIST=$(IFS=,; echo "[${BANK_BWS[*]}]")
        BW_CONFIG="--param=system.l2.per_bank_bw_budget=$BW_LIST"
    fi

    # Set up simulation parameters
    if [[ -n "$checkpoint" ]]; then
        GEM5TYPE="fast"
        CPUTYPE="AtomicSimpleCPU"
        EXTRA_CONFIG="--max-checkpoints 3 --cpu-type=$CPUTYPE"
    else
        RESTORE_CPU="ArmO3CPU"  # CPU to restore from checkpoint with
        SWITCH_CPU="ArmO3CPU"   # CPU to switch to at workbegin
        GEM5TYPE="opt"
        EXTRA_CONFIG="
            -r $RESTORE 
            --restore-with-cpu=$RESTORE_CPU
            --cpu-type=$SWITCH_CPU
        "
        
        # MSHRS configuration if specified
        if [[ -n "$MSHRS" ]]; then
            EXTRA_CONFIG="${EXTRA_CONFIG} --param=system.l2.mshrs=$MSHRS"
        fi
    fi

    setup_dirs
    
    echo "Starting gem5 simulation in directory: $RUNDIR"
    "$GEM5_DIR/build/ARM/gem5.$GEM5TYPE" --debug-flags=CacheBank,Cache,PP,PPP \
        --outdir="$RUNDIR" \
        "$GEM5_DIR"/configs/deprecated/example/fs.py \
        --kernel="$RESOURCES/vmlinux" \
        --disk="$RESOURCES/rootfs.ext2" \
        --bootloader="$RESOURCES/boot.arm64" \
        --root=/dev/sda \
        --num-cpus=$num_cpus \
        --num-l2caches=1 \
        --mem-type=DDR4_2400_16x4 \
        --mem-channels=1 \
        --mem-size=2048MB \
        --script="$GIT_ROOT/$GUEST_SCRIPT_DIR/$GUEST_SCRIPT" \
        --checkpoint-dir="$CKPT_DIR" \
        --cpu-clock=$Freq \
        $CACHE_CONFIG \
        --param=system.l2.enable_banks=True \
        --param=system.l2.enable_bw_regulation=False \
        --param=system.l2.num_banks=4 \
        --param=system.l2.bank_intlv_high_bit=0 \
        --l2_size $L2_SIZE \
        --param=system.l2.monitor_window=$MONITOR_WINDOW \
        --param=system.cpu[:].icache.enable_banks=False \
        --param=system.cpu[:].dcache.enable_banks=False \
        $BW_CONFIG \
        $EXTRA_CONFIG \
        $CPU_CONFIG
}

# Make sure RUNDIR exists before attempting redirection
mkdir -p "$RUNDIR"
# Now RUNDIR is defined and created before run_simulation is called
run_simulation > ${RUNDIR}/simout