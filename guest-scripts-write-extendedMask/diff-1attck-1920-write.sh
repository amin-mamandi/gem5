echo 256 > /proc/sys/vm/nr_hugepages
mkdir -p /mnt/huge
mount -t hugetlbfs none /mnt/huge

 
 



# bank_pll -i 30000000000 -c 0 -a write -e 1 -m 1280 -b 0x80C0 -l 16 & # attacker on data bank 0
pid1=$!

# bank_pll -i 30000000000 -c 1 -a write -e 2 -m 1280 -b 0x80C0 -l 16 & # attacker on data bank 0
pid2=$!

bank_pll -i 40000000000 -c 1 -a write -e 1 -m 320 -b 0x80C0 -l 16 -s 1 -n 1 -A -x & # attacker on data bank 0
pid3=$!






bank_pll -i 4500 -c 0 -a read -e 12 -m 1920 -b 0x80C0 -l 16 -s 0 -n 1 -x & # victim
pid4=$!


wait $pid4 
# Once the victim process exits, kill the attacker processes
echo "Victim process ended. Killing attackers..."
killall -9 bank_pll 2>/dev/null

echo "All attacker processes terminated."

# Exit
m5 exit
