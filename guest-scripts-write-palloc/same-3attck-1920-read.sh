mount -t debugfs none /sys/kernel/debug
mount -t tmpfs cgroup_root /sys/fs/cgroup
mkdir /sys/fs/cgroup/palloc
mount -t cgroup palloc -o palloc /sys/fs/cgroup/palloc/
 
mkdir /sys/fs/cgroup/palloc/part1
mkdir /sys/fs/cgroup/palloc/part2
 
echo 4 > /sys/kernel/debug/palloc/alloc_balance
echo 1 > /sys/kernel/debug/palloc/use_palloc
echo 0x1E000 > /sys/kernel/debug/palloc/palloc_mask

echo 0-7 > /sys/fs/cgroup/palloc/part1/palloc.bins
echo 8-15 > /sys/fs/cgroup/palloc/part2/palloc.bins


bank_pll -i 40000000000 -c 1 -a read -e 0 -m 1280 -b 0xC0 -l 16 -s 1 -n 3 -A & # attacker on data bank 0
pid1=$!

bank_pll -i 40000000000 -c 2 -a read -e 0 -m 1280 -b 0xC0 -l 16 -s 2 -n 3 -A & # attacker on data bank 0
pid2=$!

bank_pll -i 40000000000 -c 3 -a read -e 0 -m 1280 -b 0xC0 -l 16 -s 3 -n 3 -A & # attacker on data bank 0
pid3=$!


# Start victim after CPU switch
echo "Attacker PIDs: $pid1
 $pid2 $pid3"

echo $pid1 > /sys/fs/cgroup/palloc/part1/cgroup.procs
echo $pid2 > /sys/fs/cgroup/palloc/part1/cgroup.procs
echo $pid3 > /sys/fs/cgroup/palloc/part1/cgroup.procs

bank_pll -i 150 -c 0 -a read -e 0 -m 1920 -b 0xC0 -l 16 -s 0 -n 3 & # victim
pid4=$!
echo "Victim PID: $pid4"
echo $pid4 > /sys/fs/cgroup/palloc/part2/cgroup.procs

wait


# Exit
m5 exit
