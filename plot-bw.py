import matplotlib.pyplot as plt
import re
import csv

# Function to parse the data from the file
def parse_data(filename):
    data = []
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Get header row
        for row in reader:
            entry = {}
            for i, header in enumerate(headers):
                entry[header] = row[i]
            data.append(entry)
    return data

# Function to extract info from directory name
def extract_info(directory):
    # Extract prefix (diff, same, solo)
    prefix = directory.split('-')[0]
    
    # Extract attack number
    attack_match = re.search(r'(\d+)attck', directory)
    attack_num = int(attack_match.group(1)) if attack_match else None
    
    # Extract size
    size_match = re.search(r'-(\d+)-', directory)
    size = int(size_match.group(1)) if size_match else None
    
    # Extract operation (read/write)
    op_match = re.search(r'-(read|write)\.sh', directory)
    operation = op_match.group(1) if op_match else None
    
    return prefix, attack_num, size, operation

# Parse the data file
data = parse_data('results.csv')

# Process each entry
for entry in data:
    prefix, attack_num, size, operation = extract_info(entry['directory'])
    entry['prefix'] = prefix
    entry['attack_num'] = attack_num
    entry['size'] = size
    entry['operation'] = operation
    
    # Convert bandwidth to float, or None if N/A
    if entry['bandwidth_MBps'] != 'N/A':
        entry['bandwidth_MBps'] = float(entry['bandwidth_MBps'])
    else:
        entry['bandwidth_MBps'] = None
    
    # Convert L2 miss rate to float
    entry['l2_missrate'] = float(entry['l2_missrate'])

# Split the data by prefix
solo_data = [entry for entry in data if entry['prefix'] == 'solo']
diff_data = [entry for entry in data if entry['prefix'] == 'diff']
same_data = [entry for entry in data if entry['prefix'] == 'same']

# Function to create grouped bar plots differentiating by number of attackers
def create_grouped_bar_plot(data_subset, title, filename):
    # Get unique sizes and sort them
    sizes = set(entry['size'] for entry in data_subset)
    sizes = sorted(list(sizes))
    
    # Get unique attack numbers and sort them
    attack_nums = set(entry['attack_num'] for entry in data_subset)
    attack_nums = sorted(list(attack_nums))
    
    # For solo data, we might not have attack_num
    if not attack_nums and data_subset == solo_data:
        attack_nums = [4]  # Use 4 for solo as seen in the data
    
    # Create figures for read and write operations separately
    fig_bw_read, ax_bw_read = plt.subplots(figsize=(12, 6))
    fig_bw_write, ax_bw_write = plt.subplots(figsize=(12, 6))
    fig_miss_read, ax_miss_read = plt.subplots(figsize=(12, 6))
    fig_miss_write, ax_miss_write = plt.subplots(figsize=(12, 6))
    
    # Set width of bar
    bar_width = 0.2
    num_attacks = len(attack_nums)
    
    # Set positions of bars on X axis
    indices = list(range(len(sizes)))
    
    # Define colors for different attack numbers
    colors = ['blue', 'green', 'red', 'purple', 'orange']
    
    # Process data for read operations (bandwidth)
    for i, attack in enumerate(attack_nums):
        bw_values = []
        for size in sizes:
            # Filter for this attack number, size, and read operation
            matching_entries = [e for e in data_subset if e['attack_num'] == attack 
                               and e['size'] == size and e['operation'] == 'read']
            
            # Calculate average bandwidth if entries exist
            if matching_entries:
                valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                if valid_bw:
                    bw_values.append(sum(valid_bw) / len(valid_bw) / 1e6)  # Convert to GB/s
                else:
                    bw_values.append(0)
            else:
                bw_values.append(0)
        
        # Calculate position adjustment
        pos_adjustment = -bar_width * (num_attacks-1)/2 + i * bar_width
        positions = [idx + pos_adjustment for idx in indices]
        
        # Plot on read bandwidth chart
        ax_bw_read.bar(positions, bw_values, bar_width, 
                     label=f'{attack} Attacker(s)', color=colors[i % len(colors)])
    
    # Process data for write operations (bandwidth)
    for i, attack in enumerate(attack_nums):
        bw_values = []
        for size in sizes:
            # Filter for this attack number, size, and write operation
            matching_entries = [e for e in data_subset if e['attack_num'] == attack 
                               and e['size'] == size and e['operation'] == 'write']
            
            # Calculate average bandwidth if entries exist
            if matching_entries:
                valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                if valid_bw:
                    bw_values.append(sum(valid_bw) / len(valid_bw) / 1e6)  # Convert to GB/s
                else:
                    bw_values.append(0)
            else:
                bw_values.append(0)
        
        # Calculate position adjustment
        pos_adjustment = -bar_width * (num_attacks-1)/2 + i * bar_width
        positions = [idx + pos_adjustment for idx in indices]
        
        # Plot on write bandwidth chart
        ax_bw_write.bar(positions, bw_values, bar_width, 
                      label=f'{attack} Attacker(s)', color=colors[i % len(colors)])
    
    # Process data for read operations (miss rate)
    for i, attack in enumerate(attack_nums):
        miss_values = []
        for size in sizes:
            # Filter for this attack number, size, and read operation
            matching_entries = [e for e in data_subset if e['attack_num'] == attack 
                               and e['size'] == size and e['operation'] == 'read']
            
            # Calculate average miss rate if entries exist
            if matching_entries:
                miss_values.append(sum(e['l2_missrate'] for e in matching_entries) / len(matching_entries))
            else:
                miss_values.append(0)
        
        # Calculate position adjustment
        pos_adjustment = -bar_width * (num_attacks-1)/2 + i * bar_width
        positions = [idx + pos_adjustment for idx in indices]
        
        # Plot on read miss rate chart
        ax_miss_read.bar(positions, miss_values, bar_width, 
                       label=f'{attack} Attacker(s)', color=colors[i % len(colors)])
    
    # Process data for write operations (miss rate)
    for i, attack in enumerate(attack_nums):
        miss_values = []
        for size in sizes:
            # Filter for this attack number, size, and write operation
            matching_entries = [e for e in data_subset if e['attack_num'] == attack 
                               and e['size'] == size and e['operation'] == 'write']
            
            # Calculate average miss rate if entries exist
            if matching_entries:
                miss_values.append(sum(e['l2_missrate'] for e in matching_entries) / len(matching_entries))
            else:
                miss_values.append(0)
        
        # Calculate position adjustment
        pos_adjustment = -bar_width * (num_attacks-1)/2 + i * bar_width
        positions = [idx + pos_adjustment for idx in indices]
        
        # Plot on write miss rate chart
        ax_miss_write.bar(positions, miss_values, bar_width, 
                        label=f'{attack} Attacker(s)', color=colors[i % len(colors)])
    
    # Configure read bandwidth plot
    ax_bw_read.set_title(f'Read Bandwidth by Size - {title}')
    ax_bw_read.set_xlabel('Size')
    ax_bw_read.set_ylabel('Bandwidth (GB/s)')
    ax_bw_read.set_xticks(indices)
    ax_bw_read.set_xticklabels(sizes)
    ax_bw_read.legend()
    ax_bw_read.grid(axis='y', linestyle='--', alpha=0.7)
    ax_bw_read.set_ylim(0, 15)  # Set y-axis limit to 0-1
    
    # Configure write bandwidth plot
    ax_bw_write.set_title(f'Write Bandwidth by Size - {title}')
    ax_bw_write.set_xlabel('Size')
    ax_bw_write.set_ylabel('Bandwidth (GB/s)')
    ax_bw_write.set_xticks(indices)
    ax_bw_write.set_xticklabels(sizes)
    ax_bw_write.legend()
    ax_bw_write.grid(axis='y', linestyle='--', alpha=0.7)
    ax_bw_write.set_ylim(0, 15)  # Set y-axis limit to 0-1
    
    # Configure read miss rate plot
    ax_miss_read.set_title(f'Read L2 Miss Rate by Size - {title}')
    ax_miss_read.set_xlabel('Size')
    ax_miss_read.set_ylabel('L2 Miss Rate')
    ax_miss_read.set_xticks(indices)
    ax_miss_read.set_xticklabels(sizes)
    ax_miss_read.legend()
    ax_miss_read.grid(axis='y', linestyle='--', alpha=0.7)
    ax_miss_read.set_ylim(0, 1)  # Set y-axis limit to 0-1
    
    # Configure write miss rate plot
    ax_miss_write.set_title(f'Write L2 Miss Rate by Size - {title}')
    ax_miss_write.set_xlabel('Size')
    ax_miss_write.set_ylabel('L2 Miss Rate')
    ax_miss_write.set_xticks(indices)
    ax_miss_write.set_xticklabels(sizes)
    ax_miss_write.legend()
    ax_miss_write.grid(axis='y', linestyle='--', alpha=0.7)
    ax_miss_write.set_ylim(0, 1)  # Set y-axis limit to 0-1
    
    # Save all plots
    fig_bw_read.tight_layout()
    fig_bw_read.savefig(f'{filename}_read_bandwidth.png')
    
    fig_bw_write.tight_layout()
    fig_bw_write.savefig(f'{filename}_write_bandwidth.png')
    
    fig_miss_read.tight_layout()
    fig_miss_read.savefig(f'{filename}_read_missrate.png')
    
    fig_miss_write.tight_layout()
    fig_miss_write.savefig(f'{filename}_write_missrate.png')
    
    plt.close('all')

# Create plots for each category
create_grouped_bar_plot(solo_data, 'Solo', 'solo')
create_grouped_bar_plot(diff_data, 'Different Banks', 'diff')
create_grouped_bar_plot(same_data, 'Same Banks', 'same')

# Create a comprehensive comparison plot for miss rates across all configurations
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Get unique sizes
sizes = set(entry['size'] for entry in data)
sizes = sorted(list(sizes))

# Set width of bars
bar_width = 0.25

# Set x positions
x_positions = list(range(len(sizes)))

# Calculate average miss rates for each configuration and operation
for ax, operation in zip([ax1, ax2], ['read', 'write']):
    for i, (prefix_data, color, label) in enumerate([
        (diff_data, 'blue', 'Different Banks'),
        (same_data, 'red', 'Same Banks'),
        (solo_data, 'green', 'Solo')
    ]):
        miss_rates = []
        for size in sizes:
            matching_entries = [e for e in prefix_data if e['size'] == size and e['operation'] == operation]
            if matching_entries:
                miss_rates.append(sum(e['l2_missrate'] for e in matching_entries) / len(matching_entries))
            else:
                miss_rates.append(0)
        
        # Offset bars
        offset = -bar_width + i * bar_width
        positions = [x + offset for x in x_positions]
        
        ax.bar(positions, miss_rates, bar_width, color=color, label=label)
    
    # Configure plot
    ax.set_title(f'{operation.capitalize()} L2 Miss Rate Comparison')
    ax.set_xlabel('Size')
    ax.set_ylabel('L2 Miss Rate')
    ax.set_xticks(x_positions)
    ax.set_xticklabels(sizes)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_ylim(0, 1)  # Set y-axis limit to 0-1

fig.tight_layout()
fig.savefig('comparison_by_operation.png')

print("Plots have been created with fixed y-axis scale from 0 to 1:")
print("- Solo plots: solo_read_bandwidth.png, solo_write_bandwidth.png, solo_read_missrate.png, solo_write_missrate.png")
print("- Diff plots: diff_read_bandwidth.png, diff_write_bandwidth.png, diff_read_missrate.png, diff_write_missrate.png")
print("- Same plots: same_read_bandwidth.png, same_write_bandwidth.png, same_read_missrate.png, same_write_missrate.png")
print("- Comparison: comparison_by_operation.png")