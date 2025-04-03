# Start victim after CPU switch
bank_pll -i 150 -c 0 -a write -e 3 -m 10240 -b 0xC0 -l 16 -x & # victim
wait

# Exit
