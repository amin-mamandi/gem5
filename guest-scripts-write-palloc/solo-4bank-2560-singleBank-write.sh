# Start victim after CPU switch
bank_pll -i 150 -c 0 -a write -e 0 -m 2560 -b 0xC0 -l 16 -s 0 -n 0 # victim

# Exit
m5 exit
