# Start victim after CPU switch
bank_pll -i 150 -c 0 -a read -e 3 -m 10240 -b 0xC0 -l 16 & # victim
wait

# Exit
