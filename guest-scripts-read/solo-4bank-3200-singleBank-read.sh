# Start victim after CPU switch
bank_pll -i 50 -c 0 -a read -e 3 -m 3200 -b 0xC0 -l 16 -x & # victim
wait

# Exit
