# bank_pll -i 30000000000 -c 0 -a read -e 1 -m 1280 -b 0xC0 -l 16 & # attacker on data bank 0
bank_pll -i 40000000000 -c 1 -a read -e 0 -m 1280 -b 0xC0 -l 16 -s 1 -n 2 -A -x & # attacker on data bank 0
bank_pll -i 40000000000 -c 2 -a read -e 0 -m 1280 -b 0xC0 -l 16 -s 2 -n 2 -A -x & # attacker on data bank 0

# Start victim after CPU switch
bank_pll -i 150 -c 0 -a read -e 0 -m 3200 -b 0xC0 -l 16 -s 0 -n 2 -x & # victim
wait


# Exit
m5 exit