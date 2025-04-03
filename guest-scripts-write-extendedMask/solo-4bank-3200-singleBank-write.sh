echo 256 > /proc/sys/vm/nr_hugepages
mkdir -p /mnt/huge
mount -t hugetlbfs none /mnt/huge

 
 


bank_pll -i 4500 -c 0 -a write -e 0 -m 3200 -b 0x80C0 -l 16 -s 0 -n 0 -x & # victim
pid1=$!


wait 

# Exit
m5 exit
