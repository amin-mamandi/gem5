mount -t debugfs none /sys/kernel/debug

mount -t tmpfs cgroup_root /sys/fs/cgroup
mkdir /sys/fs/cgroup/palloc
mount -t cgroup palloc -o palloc /sys/fs/cgroup/palloc/
 
mkdir /sys/fs/cgroup/palloc/part1
mkdir /sys/fs/cgroup/palloc/part2
mkdir /sys/fs/cgroup/palloc/part3
mkdir /sys/fs/cgroup/palloc/part4
 
echo 4 > /sys/kernel/debug/palloc/alloc_balance
echo 1 > /sys/kernel/debug/palloc/use_palloc
echo 0xC000 > /sys/kernel/debug/palloc/palloc_mask

echo 0 > /sys/fs/cgroup/palloc/part1/palloc.bins
echo 1 > /sys/fs/cgroup/palloc/part2/palloc.bins
echo 2 > /sys/fs/cgroup/palloc/part3/palloc.bins
echo 3 > /sys/fs/cgroup/palloc/part4/palloc.bins


bank_pll -i 500 -c 0 -a write -e 0 -m 1280 -b 0xC0 -l 16 -s 0 -n 0 &  # victim
pid1=$!
echo "Victim PID: $pid1"
echo $pid1 > /sys/fs/cgroup/palloc/part2/cgroup.procs

cat  /sys/fs/cgroup/palloc/part2/cgroup.procs
wait 


# Exit
m5 exit
