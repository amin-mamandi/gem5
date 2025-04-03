bank_pll -i 40000000000 -c 1 -a write -e 0 -m 1280 -b 0xC0 -l 16 -s 1 -n 3 -A -x & # attacker on data bank 0
bank_pll -i 40000000000 -c 2 -a write -e 0 -m 1280 -b 0xC0 -l 16 -s 2 -n 3 -A -x & # attacker on data bank 0
bank_pll -i 40000000000 -c 3 -a write -e 0 -m 1280 -b 0xC0 -l 16 -s 3 -n 3 -A -x & # attacker on data bank 0

# Start victim after CPU switch
bank_pll -i 150 -c 0 -a read -e 0 -m 5120 -b 0xC0 -l 16 -s 0 -n 3 -x & # victim
wait


# Exit
m5 exit