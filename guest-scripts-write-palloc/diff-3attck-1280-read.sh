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

# Run attackers one by one and capture PIDs properly
echo "Attacker PIDs: $pid1
"


bank_pll -i 40000000000 -c 1 -a read -e 1 -m 1280 -b 0xC0 -l 16 -s 1 -n 3 -A &
pid1=$!
echo "Victim PID: $pid1"
echo $pid1 > /sys/fs/cgroup/palloc/part2/cgroup.procs

pid1=$!
bank_pll -i 40000000000 -c 2 -a read -e 2 -m 1280 -b 0xC0 -l 16 -s 2 -n 3 -A &
pid2=$!
bank_pll -i 40000000000 -c 3 -a read -e 3 -m 1280 -b 0xC0 -l 16 -s 3 -n 3 -A &
pid3=$!

echo "Attacker PIDs: $pid1 $pid2 $pid3"

# Set PIDs to cgroup one by one
echo $pid1 > /sys/fs/cgroup/palloc/part1/cgroup.procs
echo $pid2 > /sys/fs/cgroup/palloc/part1/cgroup.procs
echo $pid3 > /sys/fs/cgroup/palloc/part1/cgroup.procs

# Start victim and add to its cgroup
bank_pll -i 150 -c 0 -a read -e 0 -m 1280 -b 0xC0 -l 16 -s 0 -n 3 &
pid4=$!
echo "Victim PID: $pid4"
echo $pid4 > /sys/fs/cgroup/palloc/part2/cgroup.procs

wait

# Exit
m5 exit
