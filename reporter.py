import sys
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.gridspec as gridspec
import numpy as np
from matplotlib.patches import Rectangle


# --- CONFIG ---
DATA_FILE = sys.argv[1] if len(sys.argv) > 1 else "USB_Meter_Log_20250425_234827.csv"
OUTPUT_PDF = DATA_FILE.replace('.csv', '_report.pdf')
AUTHOR = "Dylan"
TEST_TYPE = "Discharge Test"

# --- Load CSV Data ---
columns = {}
with open(DATA_FILE, 'r') as f:
    reader = csv.DictReader(f, delimiter=',')
    for row in reader:
        for key, value in row.items():
            columns.setdefault(key, []).append(float(value))

# --- Extract Data ---
timestamp = columns['Timestamp (s)']
voltage = columns['Voltage (V)']
current = columns['Current (A)']
power = columns['Power (W)']
temperature = columns['Temperature (C)']
mAh = columns['mAh']

# --- Detect True Start ---
start_index = next(i for i, v in enumerate(voltage) if v > 0.1 and current[i] > 0.01)

# --- Compute Summary ---
start_voltage = voltage[start_index]
end_voltage = voltage[-1]
start_current = current[start_index]
end_current = current[-1]
start_temp = temperature[start_index]
end_temp = temperature[-1]
start_time = timestamp[start_index]
end_time = timestamp[-1]
total_duration = end_time - start_time
total_mAh = mAh[-1] - mAh[start_index]

avg_voltage = np.mean(voltage[start_index:])
avg_current = np.mean(current[start_index:])
avg_power = np.mean(power[start_index:])
avg_temp = np.mean(temperature[start_index:])

summary_text = f"""
USB Power Bank Test Report
Prepared by: {AUTHOR}
Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Test Type: {TEST_TYPE}

--- Summary ---
Duration: {total_duration:.2f} seconds
Starting Voltage: {start_voltage:.4f} V
Ending Voltage: {end_voltage:.4f} V
Starting Current: {start_current:.4f} A
Ending Current: {end_current:.4f} A
Starting Temperature: {start_temp:.2f} °C
Ending Temperature: {end_temp:.2f} °C
Total Delivered Capacity: {total_mAh:.3f} mAh

--- Averages ---
Average Voltage: {avg_voltage:.4f} V
Average Current: {avg_current:.4f} A
Average Power: {avg_power:.4f} W
Average Temperature: {avg_temp:.2f} °C
"""

# --- Plot and Save ---
with PdfPages(OUTPUT_PDF) as pdf:
    fig = plt.figure(figsize=(11, 8.5))  # Landscape letter
    gs = gridspec.GridSpec(3, 2, width_ratios=[1, 2], wspace=0.4, hspace=0.5)

    # Left: Text block
    ax_summary = fig.add_subplot(gs[:, 0])
    ax_summary.axis('off')
    ax_summary.text(0, 1, summary_text, fontsize=10, va='top', family='monospace')

    # Right: Plots inside a bordered box
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 1])
    ax3 = fig.add_subplot(gs[2, 1])

    for ax in [ax1, ax2, ax3]:
        ax.grid(True)

    ax1.plot(timestamp, voltage, label="Voltage (V)", color='tab:blue')
    ax1.set_ylabel("Voltage (V)", color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax1b = ax1.twinx()
    ax1b.plot(timestamp, current, label="Current (A)", color='tab:red')
    ax1b.set_ylabel("Current (A)", color='tab:red')
    ax1b.tick_params(axis='y', labelcolor='tab:red')
    ax1.set_title("Voltage and Current")

    ax2.plot(timestamp, power, color='tab:orange')
    ax2.set_ylabel("Power (W)")
    ax2.set_title("Power")

    ax3.plot(timestamp, temperature, color='tab:green')
    ax3.set_ylabel("Temperature (C)")
    ax3.set_xlabel("Time (s)")
    ax3.set_title("Temperature")

    # Draw border box around right plots
    fig.patches.extend([
        Rectangle(
            (0.422, 0.05), 0.53, 0.9,  # (x,y), width, height in figure coords
            fill=False, linewidth=2, edgecolor='black', zorder=10,
            transform=fig.transFigure, figure=fig
        )
    ])

    fig.patches.extend([
        Rectangle(
            (0.05, 0.05), 0.9, 0.9,  # (x,y), width, height in figure coords
            fill=False, linewidth=2, edgecolor='black', zorder=10,
            transform=fig.transFigure, figure=fig
        )
    ])

    pdf.savefig(fig)
    plt.close()

print(f"✅ Report generated: {OUTPUT_PDF}")
