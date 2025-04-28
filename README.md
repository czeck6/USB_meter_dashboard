# USB Meter Dashboard and Report Generator
FNB58 USB Power Meter Logging Program

# USB Power Meter Data Logger and Report Generator

A Python-based graphical tool to interface with an **FNB58 USB power meter** device, log live voltage/current/power data, and automatically generate a **PDF report** after a test run.

---

## ✨ Features

- **Real-time display** of voltage (V), current (A), power (W), and temperature (°C)
- **Data logging** to timestamped CSV files automatically
- **Session reset** at any time (generates separate logs for multiple tests)
- **Automatic PDF report generation** summarizing results with graphs and key metrics
- **Cross-platform:** Windows and Linux friendly
- **No sudo required** on Windows

---

## 📦 Requirements

- Python 3.7+
- Required libraries:
  - `pyusb`
  - `pyqt5`
  - `pyqtgraph`
  - `matplotlib`
  - `numpy`

You can install all dependencies via:

```bash
pip install pyusb pyqt5 pyqtgraph matplotlib numpy
```

---

## 🚀 How to Use

1. Connect your **FNB58 USB power meter** to your computer.
2. Run the main dashboard:

```bash
python 3usb_meter.py
```

3. The live dashboard window will open:
   - You can monitor voltage, current, power, and temperature in real time.
   - Click **Reset Session** to close and finalize the current session and start a new one.
   - When you **close the app** or **reset the session**, a PDF report will automatically be created based on the logged data.

---

## 🛠 How it Works

- `3usb_meter.py`:
  - Talks to the FNB58 over USB using its known Vendor and Product IDs.
  - Collects measurement data every second.
  - Displays live updating graphs with smoothing options.
  - Saves all measurements to a timestamped `.csv` file.

- `reporter.py`:
  - Parses the `.csv` file after a test run.
  - Summarizes the start/end/average values of voltage, current, power, temperature, and mAh delivered.
  - Generates a **professional-looking PDF report** with summary text and graphs.
  - PDF is saved alongside the CSV file automatically.

---

## 📸 Example Output

- CSV log files like:

```
USB_Meter_Log_20250428_140512.csv
```

- Automatically generated PDF reports like:

```
USB_Meter_Log_20250428_140512_report.pdf
```

Each PDF includes:
- Test metadata
- Start/End statistics
- Average values
- Graphs of Voltage/Current, Power, and Temperature over time

---

## 🙏 Credits and Thanks

**Special thanks to [baryluk](https://github.com/baryluk/fnirsi-usb-power-data-logger)**  
for his excellent reverse-engineering work on the FNB58 protocol.  
This project builds on his findings to create a fully automated, user-friendly dashboard and reporting tool.

---
