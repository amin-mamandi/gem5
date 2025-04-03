# bank_pll -i 30000000000 -c 0 -a write -e 1 -m 1280 -b 0xC0 -l 16 & # attacker on data bank 0
# bank_pll -i 30000000000 -c 1 -a write -e 2 -m 1280 -b 0xC0 -l 16 & # attacker on data bank 0
bank_pll -i 150000000000 -c 1 -a write -e 0 -m 1280 -b 0xC0 -l 16 -s 1 -n 1 -A -x & # attacker on data bank 0

# Start victim after CPU switch
bank_pll -i 150 -c 0 -a read -e 0 -m 640 -b 0xC0 -l 16 -s 0 -n 1 -x & # victim
wait


# Exit
m5 exit