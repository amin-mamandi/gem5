# Start victim after CPU switch
bank_pll -i 50 -c 0 -a read -e 3 -m 5120 -b 0xC0 -l 16 & # victim
wait

# Exit
