echo 256 > /proc/sys/vm/nr_hugepages
mkdir -p /mnt/huge
mount -t hugetlbfs none /mnt/huge

# Attackers use partition 0 (bits 15-14 = 00) and their original bank selections
bank_pll -i 40000000000 -c 1 -a write -e 1 -m 320 -b 0x80C0 -l 16 -s 1 -n 3 -A -x & # bank 01, partition 00
pid1=$!

bank_pll -i 40000000000 -c 2 -a write -e 2 -m 320 -b 0x80C0 -l 16 -s 2 -n 3 -A -x & # bank 10, partition 00
pid2=$!

bank_pll -i 40000000000 -c 3 -a write -e 3 -m 320 -b 0x80C0 -l 16 -s 3 -n 3 -A -x & # bank 11, partition 00
pid3=$!

# Victim uses partition 3 (bits 15-14 = 11) and the same bank as in your original script
# For example, if your original victim used bank 0 (bits 7-6 = 00), that would be:
bank_pll -i 4500 -c 0 -a read -e 12 -m 10240 -b 0x80C0 -l 16 -s 0 -n 3 -x & # bank 00, partition 11
pid4=$!

wait $pid4 
# Once the victim process exits, kill the attacker processes
echo "Victim process ended. Killing attackers..."
killall -9 bank_pll 2>/dev/null

echo "All attacker processes terminated."

# Exit
m5 exit