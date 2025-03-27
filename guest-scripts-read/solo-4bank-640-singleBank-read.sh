# Start victim after CPU switch
bank_pll -i 50 -c 0 -a read -e 3 -m 640 -b 0xC0 -l 16 & # victim
bank_pll -i 50 -c 2 -a read -e 2 -m 640 -b 0xC0 -l 16 & # victim

wait

# Exit
