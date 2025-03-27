# bank_pll -i 30000000000 -c 0 -a read -e 1 -m 1280 -b 0xC0 -l 16 & # attacker on data bank 0
bank_pll -i 30000000000 -c 1 -a read -e 1 -m 1280 -b 0xC0 -l 16 & # attacker on data bank 0
bank_pll -i 30000000000 -c 2 -a read -e 2 -m 1280 -b 0xC0 -l 16 & # attacker on data bank 0
sleep 1 # Increased sleep duration to ensure attackers are fully started

# Start victim after CPU switch
bank_pll -i 50 -c 0 -a read -e 0 -m 1920 -b 0xC0 -l 16 & # victim
wait


# Exit
m5 exit