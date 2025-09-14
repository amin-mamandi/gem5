#!/bin/bash

######################### ddr / hbm memory #########################

base_checkpoint_dir="/home/HBM/gem5-runs/base-ckpt"


solo_command() {
    local dimension=$1
    local algorithm=$2
    local mode=$3
    echo "matrix --affinity 3 --hugepage --dimension $dimension --mode $mode --algorithm $algorithm; m5 exit;"
}


corun_single_bank_ddr_commands() {
    local dimension=$1
    local algorithm=$2
    local mode=$3

cat <<EOF
    # Attacker 1
    bankpll -m 8192 --attacker --num-attackers 3 --sync-id 1 \
        --affinity 0 -l 16 --repeat 40000000 --access write --hugepage \
        --bank 0 -B 0x1E000 & 
    PID1=\$!

    # Attacker 2
    bankpll -m 8192 --attacker --num-attackers 3 --sync-id 2 \
        --affinity 1 -l 16 --repeat 40000000 --access write --hugepage \
        --bank 0 -B 0x1E000 & 
    PID2=\$!

    # Attacker 3
    bankpll -m 8192 --attacker --num-attackers 3 --sync-id 3 \
        --affinity 2 -l 16 --repeat 40000000 --access write --hugepage \
        --bank 0 -B 0x1E000 & 
    PID3=\$!

    # Victim
    matrix -f 3 -x -d $dimension --mode $mode --algorithm $algorithm -i 0 -n 3

    # Terminate attackers
    kill -TERM \$PID1 \$PID2 \$PID3
    wait \$PID1 \$PID2 \$PID3

    m5 exit
EOF
}

# corun_all_banks_ddr_commands() {
#     local dimension=$1
#     local algorithm=$2
#     local mode=$3

# cat <<EOF
#     # Attacker 1
#     bankpll -m 8192 --attacker --num-attackers 3 --sync-id 1 \
#         --affinity 0 -l 16 --repeat 40000000 --access write --hugepage \
#         -B 0x1E000 & 
#     PID1=\$!

#     # Attacker 2
#     bankpll -m 8192 --attacker --num-attackers 3 --sync-id 2 \
#         --affinity 1 -l 16 --repeat 40000000 --access write --hugepage \
#         -B 0x1E000 &
#     PID2=\$!

#     # Attacker 3
#     bankpll -m 8192 --attacker --num-attackers 3 --sync-id 3 \
#         --affinity 2 -l 16 --repeat 40000000 --access write --hugepage \
#         -B 0x1E000 & 
#     PID3=\$!

#     # Victim
#     matrix --affinity 3 --sync-id 0 --num-attackers 3 --hugepage --dimension $dimension --mode $mode --algorithm $algorithm;

#     # Terminate attackers
#     kill -TERM \$PID1 \$PID2 \$PID3
#     wait \$PID1 \$PID2 \$PID3

#     m5 exit
# EOF
# }


corun_single_bank_hbm_commands() {
    local dimension=$1
    local algorithm=$2
    local mode=$3

cat <<EOF
    # Attacker 1
    bankpll -m 8192 --attacker --num-attackers 3 --sync-id 1 \
        --affinity 0 -l 16 --repeat 40000000 --access write --hugepage \
        --channel 0 --pseudo 0 --bank 0 -B 0x3C000 -P 0x40 -C 0xE00 & 
    PID1=\$!

    # Attacker 2
    bankpll -m 8192 --attacker --num-attackers 3 --sync-id 2 \
        --affinity 1 -l 16 --repeat 40000000 --access write --hugepage \
        --channel 0 --pseudo 0 --bank 0 -B 0x3C000 -P 0x40 -C 0xE00 & 
    PID2=\$!

    # Attacker 3
    bankpll -m 8192 --attacker --num-attackers 3 --sync-id 3 \
        --affinity 2 -l 16 --repeat 40000000 --access write --hugepage \
        --channel 0 --pseudo 0 --bank 0 -B 0x3C000 -P 0x40 -C 0xE00 & 
    PID3=\$!

    # Victim
    matrix -f 3 -x -d $dimension --mode $mode --algorithm $algorithm -i 0 -n 3

    # Terminate attackers
    kill -TERM \$PID1 \$PID2 \$PID3
    wait \$PID1 \$PID2 \$PID3

    m5 exit
EOF
}

corun_all_banks_commands() {
    local dimension=$1
    local algorithm=$2
    local mode=$3

cat <<EOF
    # Attacker 1
    bankpll -m 8192 --attacker --num-attackers 3 --sync-id 1 \
        --affinity 0 -l 16 --repeat 40000000 --access write --hugepage \
         -B 0x3C000 -P 0x40 -C 0xE00 & 
    PID1=\$!

    # Attacker 2
    bankpll -m 8192 --attacker --num-attackers 3 --sync-id 2 \
        --affinity 1 -l 16 --repeat 40000000 --access write --hugepage \
        -B 0x3C000 -P 0x40 -C 0xE00 & 
    PID2=\$!

    # Attacker 3
    bankpll -m 8192 --attacker --num-attackers 3 --sync-id 3 \
        --affinity 2 -l 16 --repeat 40000000 --access write --hugepage \
        -B 0x3C000 -P 0x40 -C 0xE00 & 
    PID3=\$!

    # Victim
    matrix -f 3 -x -d $dimension --mode $mode --algorithm $algorithm -i 0 -n 3

    # Terminate attackers
    kill -TERM \$PID1 \$PID2 \$PID3
    wait \$PID1 \$PID2 \$PID3

    m5 exit
EOF
}


latest_checkpoint() {
    local run_dir=$1
    # List checkpoint dirs, extract the numbers, sort numerically, take the max
    local latest=$(ls -d "$run_dir"/cpt.* 2>/dev/null | sort -t. -k2 -n | tail -1)
    echo "$latest"
}

# Define common parameters
common_args=(
    configs/example/gem5_library/arm-ubuntu-run-myVersion.py
    -m classic
    -c o3
    -n 4
)


# Loop through configurations
# for dimension in 512 1024; do
#     for mem_type in "hbm"; do
#         for opt_level in 1 0; do
#             # Set output directory
#             outdir="/home/HBM/gem5-runs/solo-gemm-opt${opt_level}-${mem_type}-${dimension}"
#             outdir_ddr="/home/HBM/gem5-runs/solo-gemm-opt${opt_level}-ddr-${dimension}"


#             # Set algorithm (matrix argument)
#             algorithm=$opt_level

#             # Pull latest checkpoint from this directory
#             cpt=$(latest_checkpoint "$outdir_ddr")
#             cmd="$(solo_command $dimension $algorithm 0)"
#             # Run the simulation
#             ./build/ARM/gem5.fast \
#                 --outdir "$outdir" \
#                 "${common_args[@]}" \
#                 --dram-class "$mem_type" \
#                 --checkpoint "$cpt" \
#                 --command "$cmd" &
#         done
#     done
# done

# # Loop through configurations
# for dimension in 512 1024; do
#     for mem_type in "hbm"; do
#         for opt_level in 1 0; do
#             # Set output directory
#             outdir="/home/HBM/gem5-runs/solo-gemv-opt${opt_level}-${mem_type}-${dimension}"
#             outdir_ddr="/home/HBM/gem5-runs/solo-gemv-opt${opt_level}-ddr-${dimension}"

#             # Set algorithm (matrix argument)
#             algorithm=$opt_level

#             # Pull latest checkpoint from this directory
#             cpt=$(latest_checkpoint "$outdir_ddr")
#             cmd="$(solo_command $dimension $algorithm 1)"

#             # Run the simulation
#             ./build/ARM/gem5.fast \
#                 --outdir "$outdir" \
#                 "${common_args[@]}" \
#                 --dram-class "$mem_type" \
#                 --checkpoint "$cpt" \
#                 --command "$cmd" &
#         done
#     done
# done

# # Loop through configurations
# for dimension in 512 1024; do
#     for mem_type in "hbm"; do
#         for opt_level in 1 0; do
#             # Set output directory
#             outdir="/home/HBM/gem5-runs/corun-all-gemm-opt${opt_level}-${mem_type}-${dimension}"
#             outdir_ddr="/home/HBM/gem5-runs/corun-all-gemm-opt${opt_level}-ddr-${dimension}"

#             # Set algorithm (matrix argument)
#             algorithm=$opt_level

#             # Pull latest checkpoint from this directory
#             cpt=$(latest_checkpoint "$outdir_ddr")
#             cmd="$(corun_all_banks_commands $dimension $algorithm 0)"
#             # Run the simulation
#             ./build/ARM/gem5.fast \
#                 --outdir "$outdir" \
#                 "${common_args[@]}" \
#                 --dram-class "$mem_type" \
#                 --checkpoint "$cpt" \
#                 --command "$cmd" &
#         done
#     done
# done

# # Loop through configurations
# for dimension in 512 1024; do
#     for mem_type in "hbm"; do
#         for opt_level in 1 0; do
#             # Set output directory
#             outdir="/home/HBM/gem5-runs/corun-all-gemv-opt${opt_level}-${mem_type}-${dimension}"
#             outdir_ddr="/home/HBM/gem5-runs/corun-all-gemv-opt${opt_level}-ddr-${dimension}"

#             # Set algorithm (matrix argument)
#             algorithm=$opt_level

#             # Pull latest checkpoint from this directory
#             cpt=$(latest_checkpoint "$outdir_ddr")
#             cmd="$(corun_all_banks_commands $dimension $algorithm 1)"
#             # Run the simulation
#             ./build/ARM/gem5.fast \
#                 --outdir "$outdir" \
#                 "${common_args[@]}" \
#                 --dram-class "$mem_type" \
#                 --checkpoint "$cpt" \
#                 --command "$cmd" &
#         done
#     done
# done


####################### DDR solo bank ############################


# Loop through configurations
for dimension in 512 1024; do
    for mem_type in "ddr"; do
        for opt_level in 1 0; do
            # Set output directory
            outdir="/home/HBM/gem5-runs/corun-single-gemm-opt${opt_level}-${mem_type}-${dimension}"

            # Set algorithm (matrix argument)
            algorithm=$opt_level

            # Pull latest checkpoint from this directory
            cpt=$(latest_checkpoint "$outdir")
            cmd="$(corun_single_bank_ddr_commands $dimension $algorithm 0)"
            # Run the simulation
            ./build/ARM/gem5.fast \
                --outdir "$outdir" \
                "${common_args[@]}" \
                --dram-class "$mem_type" \
                --checkpoint "$cpt" \
                --command "$cmd" &
        done
    done
done


# Loop through configurations
for dimension in 512 1024; do
    for mem_type in "ddr"; do
        for opt_level in 1 0; do
            # Set output directory
            outdir="/home/HBM/gem5-runs/corun-single-gemv-opt${opt_level}-${mem_type}-${dimension}"

            # Set algorithm (matrix argument)
            algorithm=$opt_level

            # Pull latest checkpoint from this directory
            cpt=$(latest_checkpoint "$outdir")
            cmd="$(corun_single_bank_ddr_commands $dimension $algorithm 1)"
            # Run the simulation
            ./build/ARM/gem5.fast \
                --outdir "$outdir" \
                "${common_args[@]}" \
                --dram-class "$mem_type" \
                --checkpoint "$cpt" \
                --command "$cmd" &
        done
    done
done


######################## HBM solo bank ##########################

# Loop through configurations
for dimension in 512 1024; do
    for mem_type in "hbm"; do
        for opt_level in 1 0; do
            # Set output directory
            outdir="/home/HBM/gem5-runs/corun-single-gemm-opt${opt_level}-${mem_type}-${dimension}"

            # Set algorithm (matrix argument)
            algorithm=$opt_level

            # Pull latest checkpoint from this directory
            cpt=$(latest_checkpoint "$outdir")
            cmd="$(corun_single_bank_hbm_commands $dimension $algorithm 0)"
            # Run the simulation
            ./build/ARM/gem5.fast \
                --outdir "$outdir" \
                "${common_args[@]}" \
                --dram-class "$mem_type" \
                --checkpoint "$cpt" \
                --command "$cmd" &
        done
    done
done


# Loop through configurations
for dimension in 512 1024; do
    for mem_type in "hbm"; do
        for opt_level in 1 0; do
            # Set output directory
            outdir="/home/HBM/gem5-runs/corun-single-gemv-opt${opt_level}-${mem_type}-${dimension}"

            # Set algorithm (matrix argument)
            algorithm=$opt_level

            # Pull latest checkpoint from this directory
            cpt=$(latest_checkpoint "$outdir")
            cmd="$(corun_single_bank_hbm_commands $dimension $algorithm 1)"
            # Run the simulation
            ./build/ARM/gem5.fast \
                --outdir "$outdir" \
                "${common_args[@]}" \
                --dram-class "$mem_type" \
                --checkpoint "$cpt" \
                --command "$cmd" &
        done
    done
done
