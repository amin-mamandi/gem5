import matplotlib.pyplot as plt
import re
import csv
import matplotlib.cm as cm

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

# Function to calculate slowdown (higher values mean slower performance compared to baseline)
def calculate_slowdown(baseline_bw, test_bw):
    if baseline_bw is None or test_bw is None or baseline_bw == 0 or test_bw == 0:
        return None
    return baseline_bw / test_bw

# Function to create slowdown bar plots
def create_slowdown_plot():
    # Get unique sizes and sort them
    sizes = set(entry['size'] for entry in data)
    sizes = sorted(list(sizes))
    
    # Get unique attack numbers for diff and same data
    diff_attack_nums = set(entry['attack_num'] for entry in diff_data)
    diff_attack_nums = sorted(list(diff_attack_nums))
    
    same_attack_nums = set(entry['attack_num'] for entry in same_data)
    same_attack_nums = sorted(list(same_attack_nums))
    
    # Create figures for read and write operations slowdown
    fig_read, ax_read = plt.subplots(figsize=(14, 7))
    fig_write, ax_write = plt.subplots(figsize=(14, 7))
    
    # Set width of bar
    bar_width = 0.10
    
    # Set positions of bars on X axis
    indices = list(range(len(sizes)))
    
    # Create color maps for different configurations
    # Use different color palettes from matplotlib
    diff_read_cmap = cm.get_cmap('viridis', len(diff_attack_nums))
    same_read_cmap = cm.get_cmap('plasma', len(same_attack_nums))
    diff_write_cmap = cm.get_cmap('autumn', len(diff_attack_nums))
    same_write_cmap = cm.get_cmap('winter', len(same_attack_nums))
    
    # Store legend handles and labels
    legend_handles = []
    legend_labels = []

    # First, calculate baseline performance for each size (solo-read)
    solo_read_baseline = {}
    for size in sizes:
        matching_entries = [e for e in solo_data if e['size'] == size and e['operation'] == 'read']
        if matching_entries:
            valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
            if valid_bw:
                solo_read_baseline[size] = sum(valid_bw) / len(valid_bw)
            else:
                solo_read_baseline[size] = None
        else:
            solo_read_baseline[size] = None
    
    # Process data for diff configurations (read)
    x_offset = -0.5  # Start offset for positioning
    for i, attack in enumerate(diff_attack_nums):
        slowdown_values = []
        for size in sizes:
            # Get baseline bandwidth for this size
            baseline_bw = solo_read_baseline.get(size)
            
            # Filter for this attack number, size, and read operation in diff data
            matching_entries = [e for e in diff_data if e['attack_num'] == attack 
                               and e['size'] == size and e['operation'] == 'read']
            
            # Calculate average bandwidth and then slowdown if entries exist
            if matching_entries and baseline_bw:
                valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                if valid_bw:
                    avg_bw = sum(valid_bw) / len(valid_bw)
                    slowdown = calculate_slowdown(baseline_bw, avg_bw)
                    slowdown_values.append(slowdown)
                else:
                    slowdown_values.append(None)
            else:
                slowdown_values.append(None)
        
        # Filter out None values for display
        valid_positions = []
        valid_slowdowns = []
        for idx, val in enumerate(slowdown_values):
            if val is not None:
                valid_positions.append(indices[idx] + x_offset)
                valid_slowdowns.append(val)
        
        # Plot on read slowdown chart with a unique color
        bar = ax_read.bar(valid_positions, valid_slowdowns, bar_width, 
                    color=diff_read_cmap(i))
        
        legend_handles.append(bar)
        legend_labels.append(f'Diff-{attack} Read')
        
        x_offset += bar_width
    
    # Process data for same configurations (read)
    for i, attack in enumerate(same_attack_nums):
        slowdown_values = []
        for size in sizes:
            # Get baseline bandwidth for this size
            baseline_bw = solo_read_baseline.get(size)
            
            # Filter for this attack number, size, and read operation in same data
            matching_entries = [e for e in same_data if e['attack_num'] == attack 
                               and e['size'] == size and e['operation'] == 'read']
            
            # Calculate average bandwidth and then slowdown if entries exist
            if matching_entries and baseline_bw:
                valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                if valid_bw:
                    avg_bw = sum(valid_bw) / len(valid_bw)
                    slowdown = calculate_slowdown(baseline_bw, avg_bw)
                    slowdown_values.append(slowdown)
                else:
                    slowdown_values.append(None)
            else:
                slowdown_values.append(None)
        
        # Filter out None values for display
        valid_positions = []
        valid_slowdowns = []
        for idx, val in enumerate(slowdown_values):
            if val is not None:
                valid_positions.append(indices[idx] + x_offset)
                valid_slowdowns.append(val)
        
        # Plot on read slowdown chart with a unique color
        bar = ax_read.bar(valid_positions, valid_slowdowns, bar_width, 
                    color=same_read_cmap(i))
        
        legend_handles.append(bar)
        legend_labels.append(f'Same-{attack} Read')
        
        x_offset += bar_width
    
    # Now calculate baseline performance for each size (solo-read) for write comparison
    # We still compare against solo-read as requested
    
    # Process data for diff configurations (write)
    x_offset = -0.5  # Reset offset for positioning
    for i, attack in enumerate(diff_attack_nums):
        slowdown_values = []
        for size in sizes:
            # Get baseline bandwidth for this size (still using solo-read)
            baseline_bw = solo_read_baseline.get(size)
            
            # Filter for this attack number, size, and write operation in diff data
            matching_entries = [e for e in diff_data if e['attack_num'] == attack 
                               and e['size'] == size and e['operation'] == 'write']
            
            # Calculate average bandwidth and then slowdown if entries exist
            if matching_entries and baseline_bw:
                valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                if valid_bw:
                    avg_bw = sum(valid_bw) / len(valid_bw)
                    slowdown = calculate_slowdown(baseline_bw, avg_bw)
                    slowdown_values.append(slowdown)
                else:
                    slowdown_values.append(None)
            else:
                slowdown_values.append(None)
        
        # Filter out None values for display
        valid_positions = []
        valid_slowdowns = []
        for idx, val in enumerate(slowdown_values):
            if val is not None:
                valid_positions.append(indices[idx] + x_offset)
                valid_slowdowns.append(val)
        
        # Plot on write slowdown chart with a unique color
        bar = ax_write.bar(valid_positions, valid_slowdowns, bar_width, 
                     color=diff_write_cmap(i))
        
        legend_handles.append(bar)
        legend_labels.append(f'Diff-{attack} Write')
        
        x_offset += bar_width
    
    # Process data for same configurations (write)
    for i, attack in enumerate(same_attack_nums):
        slowdown_values = []
        for size in sizes:
            # Get baseline bandwidth for this size (still using solo-read)
            baseline_bw = solo_read_baseline.get(size)
            
            # Filter for this attack number, size, and write operation in same data
            matching_entries = [e for e in same_data if e['attack_num'] == attack 
                               and e['size'] == size and e['operation'] == 'write']
            
            # Calculate average bandwidth and then slowdown if entries exist
            if matching_entries and baseline_bw:
                valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                if valid_bw:
                    avg_bw = sum(valid_bw) / len(valid_bw)
                    slowdown = calculate_slowdown(baseline_bw, avg_bw)
                    slowdown_values.append(slowdown)
                else:
                    slowdown_values.append(None)
            else:
                slowdown_values.append(None)
        
        # Filter out None values for display
        valid_positions = []
        valid_slowdowns = []
        for idx, val in enumerate(slowdown_values):
            if val is not None:
                valid_positions.append(indices[idx] + x_offset)
                valid_slowdowns.append(val)
        
        # Plot on write slowdown chart with a unique color
        bar = ax_write.bar(valid_positions, valid_slowdowns, bar_width, 
                      color=same_write_cmap(i))
        
        legend_handles.append(bar)
        legend_labels.append(f'Same-{attack} Write')
        
        x_offset += bar_width
    
    # Add a reference line at y=1 (no slowdown)
    ax_read.axhline(y=1, color='black', linestyle='--', alpha=0.7)
    ax_write.axhline(y=1, color='black', linestyle='--', alpha=0.7)
    
    # Add vertical lines between size groups
    for i in range(1, len(indices)):
        ax_read.axvline(x=i - 0.5, color='gray', linestyle='--', alpha=0.5)
        ax_write.axvline(x=i - 0.5, color='gray', linestyle='--', alpha=0.5)
    
    # Configure read slowdown plot
    ax_read.set_title('Read Performance Slowdown Relative to Solo (Higher is Worse)')
    ax_read.set_xlabel('Size')
    ax_read.set_ylabel('Slowdown Factor')
    ax_read.set_xticks(indices)
    ax_read.set_xticklabels(sizes)
    ax_read.legend(handles=legend_handles[:len(diff_attack_nums) + len(same_attack_nums)], 
                 labels=legend_labels[:len(diff_attack_nums) + len(same_attack_nums)],
                 loc='upper right')
    ax_read.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Set y-axis limits with some headroom
    max_slowdown_read = max([s for s in [val for sublist in [slowdown_values for _ in range(2*len(diff_attack_nums) + 2*len(same_attack_nums))] 
                               for val in sublist if val is not None] or [1.5]])
    ax_read.set_ylim(0, max_slowdown_read * 1.1)
    
    # Configure write slowdown plot
    ax_write.set_title('Write Performance Slowdown Relative to Solo (Higher is Worse)')
    ax_write.set_xlabel('Size')
    ax_write.set_ylabel('Slowdown Factor')
    ax_write.set_xticks(indices)
    ax_write.set_xticklabels(sizes)
    ax_write.legend(handles=legend_handles[len(diff_attack_nums) + len(same_attack_nums):], 
                  labels=legend_labels[len(diff_attack_nums) + len(same_attack_nums):],
                  loc='upper right')
    ax_write.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Set y-axis limits with some headroom
    max_slowdown_write = max([s for s in [val for sublist in [slowdown_values for _ in range(2*len(diff_attack_nums) + 2*len(same_attack_nums))] 
                                for val in sublist if val is not None] or [1.5]])
    ax_write.set_ylim(0, max_slowdown_write * 1.1)
    
    # Save plots with normal layout (legend inside)
    fig_read.tight_layout()
    fig_read.savefig('slowdown_read_vs_solo-read.png')
    
    fig_write.tight_layout()
    fig_write.savefig('slowdown_write_vs_solo-read.png')
    
    # Create a combined plot with both read and write operations
    fig_combined, ax_combined = plt.subplots(figsize=(16, 8))
    
    # Set new positions for combined plot
    x_offset = -0.44
    bar_width = 0.08
    
    # Create labels for the legend
    combined_handles = []
    combined_labels = []
    
    # Use a divergent colormap for combined plot
    combined_cmap = cm.get_cmap('tab20', len(diff_attack_nums)*2 + len(same_attack_nums)*2)
    color_index = 0
    
    # Add diff-read configurations
    for i, attack in enumerate(diff_attack_nums):
        slowdown_values = []
        for size in sizes:
            baseline_bw = solo_read_baseline.get(size)
            matching_entries = [e for e in diff_data if e['attack_num'] == attack 
                              and e['size'] == size and e['operation'] == 'read']
            
            if matching_entries and baseline_bw:
                valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                if valid_bw:
                    avg_bw = sum(valid_bw) / len(valid_bw)
                    slowdown = calculate_slowdown(baseline_bw, avg_bw)
                    slowdown_values.append(slowdown)
                else:
                    slowdown_values.append(None)
            else:
                slowdown_values.append(None)
        
        valid_positions = []
        valid_slowdowns = []
        for idx, val in enumerate(slowdown_values):
            if val is not None:
                valid_positions.append(indices[idx] + x_offset)
                valid_slowdowns.append(val)
        
        if i % 3 == 0:
            pattern = ''
        elif i % 3 == 1:
            pattern = '/'
        else:  # i % 3 == 2
            pattern = '-'
        # pattern = '--' if i % 2 == 0 else '/'
        bar = ax_combined.bar(valid_positions, valid_slowdowns, bar_width, 
                        color=combined_cmap(color_index), 
                        hatch=pattern, edgecolor='black', linewidth=0.5)
        
        combined_handles.append(bar)
        combined_labels.append(f'Diff-{attack} Read')
        
        x_offset += bar_width
        color_index += 1
    
    # Add same-read configurations
    for i, attack in enumerate(same_attack_nums):
        slowdown_values = []
        for size in sizes:
            baseline_bw = solo_read_baseline.get(size)
            matching_entries = [e for e in same_data if e['attack_num'] == attack 
                              and e['size'] == size and e['operation'] == 'read']
            
            if matching_entries and baseline_bw:
                valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                if valid_bw:
                    avg_bw = sum(valid_bw) / len(valid_bw)
                    slowdown = calculate_slowdown(baseline_bw, avg_bw)
                    slowdown_values.append(slowdown)
                else:
                    slowdown_values.append(None)
            else:
                slowdown_values.append(None)
        
        valid_positions = []
        valid_slowdowns = []
        for idx, val in enumerate(slowdown_values):
            if val is not None:
                valid_positions.append(indices[idx] + x_offset)
                valid_slowdowns.append(val)
        
        pattern = '' if i % 2 == 0 else '\\'
        bar = ax_combined.bar(valid_positions, valid_slowdowns, bar_width, 
                        color=combined_cmap(color_index), 
                        hatch=pattern, edgecolor='black', linewidth=0.5)
        
        combined_handles.append(bar)
        combined_labels.append(f'Same-{attack} Read')
        
        x_offset += bar_width
        color_index += 1
    
    # Add diff-write configurations
    for i, attack in enumerate(diff_attack_nums):
        slowdown_values = []
        for size in sizes:
            baseline_bw = solo_read_baseline.get(size)
            matching_entries = [e for e in diff_data if e['attack_num'] == attack 
                              and e['size'] == size and e['operation'] == 'write']
            
            if matching_entries and baseline_bw:
                valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                if valid_bw:
                    avg_bw = sum(valid_bw) / len(valid_bw)
                    slowdown = calculate_slowdown(baseline_bw, avg_bw)
                    slowdown_values.append(slowdown)
                else:
                    slowdown_values.append(None)
            else:
                slowdown_values.append(None)
        
        valid_positions = []
        valid_slowdowns = []
        for idx, val in enumerate(slowdown_values):
            if val is not None:
                valid_positions.append(indices[idx] + x_offset)
                valid_slowdowns.append(val)
        
        pattern = 'o' if i % 2 == 0 else 'O'
        bar = ax_combined.bar(valid_positions, valid_slowdowns, bar_width, 
                        color=combined_cmap(color_index), 
                        hatch=pattern, edgecolor='black', linewidth=0.5)
        
        combined_handles.append(bar)
        combined_labels.append(f'Diff-{attack} Write')
        
        x_offset += bar_width
        color_index += 1
    
    # Add same-write configurations
    for i, attack in enumerate(same_attack_nums):
        slowdown_values = []
        for size in sizes:
            baseline_bw = solo_read_baseline.get(size)
            matching_entries = [e for e in same_data if e['attack_num'] == attack 
                              and e['size'] == size and e['operation'] == 'write']
            
            if matching_entries and baseline_bw:
                valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                if valid_bw:
                    avg_bw = sum(valid_bw) / len(valid_bw)
                    slowdown = calculate_slowdown(baseline_bw, avg_bw)
                    slowdown_values.append(slowdown)
                else:
                    slowdown_values.append(None)
            else:
                slowdown_values.append(None)
        
        valid_positions = []
        valid_slowdowns = []
        for idx, val in enumerate(slowdown_values):
            if val is not None:
                valid_positions.append(indices[idx] + x_offset)
                valid_slowdowns.append(val)
        
        pattern = '.' if i % 2 == 0 else '*'
        bar = ax_combined.bar(valid_positions, valid_slowdowns, bar_width, 
                        color=combined_cmap(color_index), 
                        hatch=pattern, edgecolor='black', linewidth=0.5)
        
        combined_handles.append(bar)
        combined_labels.append(f'Same-{attack} Write')
        
        x_offset += bar_width
        color_index += 1
    
    # Add reference line
    ax_combined.axhline(y=1, color='black', linestyle='--', alpha=0.7)
    
    # Add vertical lines between size groups
    for i in range(1, len(indices)):
        ax_combined.axvline(x=i - 0.5, color='gray', linestyle='--', alpha=0.5)
    
    # Configure combined plot
    ax_combined.set_title('Performance Slowdown Relative to Solo (Higher is Worse)')
    ax_combined.set_xlabel('Size')
    ax_combined.set_ylabel('Slowdown Factor')
    ax_combined.set_xticks(indices)
    ax_combined.set_xticklabels(sizes)
    ax_combined.legend(handles=combined_handles, labels=combined_labels, 
                     loc='upper right', ncol=2)
    ax_combined.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Set y-axis limits with some headroom for combined plot
    all_slowdowns = []
    for config in [diff_data, same_data]:
        for op in ['read', 'write']:
            for attack in set(e['attack_num'] for e in config):
                for size in sizes:
                    baseline_bw = solo_read_baseline.get(size)
                    matching_entries = [e for e in config if e['attack_num'] == attack 
                                      and e['size'] == size and e['operation'] == op]
                    
                    if matching_entries and baseline_bw:
                        valid_bw = [e['bandwidth_MBps'] for e in matching_entries if e['bandwidth_MBps'] is not None]
                        if valid_bw:
                            avg_bw = sum(valid_bw) / len(valid_bw)
                            slowdown = calculate_slowdown(baseline_bw, avg_bw)
                            if slowdown is not None:
                                all_slowdowns.append(slowdown)
    
    max_combined_slowdown = max(all_slowdowns or [1.5])
    ax_combined.set_ylim(0, max_combined_slowdown * 1.1)
    
    # Save combined plot with normal layout (legend inside)
    fig_combined.tight_layout()
    fig_combined.savefig('slowdown_combined_vs_solo-read.png')
    
    plt.close('all')
    
    print("Slowdown plots created with unique colors:")
    print("- Read operations: slowdown_read_vs_solo-read.png")
    print("- Write operations: slowdown_write_vs_solo-read.png")
    print("- Combined operations: slowdown_combined_vs_solo-read.png")

# Create the slowdown plots
create_slowdown_plot()