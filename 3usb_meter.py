import sys
import datetime
import usb.core
import usb.util
import time
import csv
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QColor
import pyqtgraph as pg
import platform
import subprocess
import os

# --- CONFIG ---
VENDOR_ID = 0x2E3C
PRODUCT_ID = 0x5558

INIT_COMMANDS = [
    bytes([0xAA, 0x81]) + bytes(61) + bytes([0x8E]),
    bytes([0xAA, 0x82]) + bytes(61) + bytes([0x96]),
    bytes([0xAA, 0x82]) + bytes(61) + bytes([0x96]),
]
KEEPALIVE_COMMAND = bytes([0xAA, 0x83]) + bytes(61) + bytes([0x9E])

# --- USB Meter Reader ---
class USBMeterReader(QtCore.QObject):
    new_data = QtCore.pyqtSignal(dict)

    def run_reporter(self):
        try:
            log_filename = self.log_file.name  # Use the current log file's filename
            if os.path.exists("reporter.py"):
                subprocess.run(
                    ["python", "reporter.py", log_filename],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                print("Warning: reporter.py not found, skipping report generation.")
        except Exception as e:
            print(f"Error running reporter: {e}")

    def __init__(self):
        super().__init__()
        self.init_logging()
        self.device = None
        self.interface = None
        self.ep_in = None
        self.ep_out = None
        self.start_time = time.time()
        self.last_timestamp = self.start_time
        self.cumulative_mAh = 0.0

    def init_logging(self):
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.close()
        self.log_file = open(f"USB_Meter_Log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mode='w', newline='')
        self.csv_writer = csv.writer(self.log_file)
        self.csv_writer.writerow(["Timestamp (s)", "Voltage (V)", "Current (A)", "Power (W)", "Temperature (C)", "DP (V)", "DN (V)", "mAh"])


    def start(self):
        self.device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if self.device is None:
            print("Device not found")
            sys.exit(1)
        try:
            self.device.set_configuration()
        except usb.core.USBError:
            pass

        cfg = self.device.get_active_configuration()
        for i in cfg:
            if platform.system() != 'Windows':
                try:
                    if self.device.is_kernel_driver_active(i.bInterfaceNumber):
                        self.device.detach_kernel_driver(i.bInterfaceNumber)
                except (NotImplementedError, usb.core.USBError):
                    pass  # Either not supported or some devices don't like it
            if i.bInterfaceClass == 0x03:
                self.interface = i

        if self.interface is None:
            print("No HID interface found!")
            sys.exit(1)

        usb.util.claim_interface(self.device, self.interface.bInterfaceNumber)

        self.ep_out = usb.util.find_descriptor(
            self.interface,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        self.ep_in = usb.util.find_descriptor(
            self.interface,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
        )

        if not self.ep_out or not self.ep_in:
            print("Could not find endpoints!")
            sys.exit(1)

        for cmd in INIT_COMMANDS:
            try:
                self.ep_out.write(cmd)
                time.sleep(0.1)
            except usb.core.USBError as e:
                print(f"Error sending INIT_COMMAND: {e}")

        self.poll_timer = QtCore.QTimer()
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(1000)

        self.keepalive_timer = QtCore.QTimer()
        self.keepalive_timer.timeout.connect(self.send_keepalive)
        self.keepalive_timer.start(1000)

    def reinitialize(self):
        self.init_logging()
        self.start_time = time.time()
        self.last_timestamp = self.start_time
        self.cumulative_mAh = 0.0

    def send_keepalive(self):
        try:
            self.ep_out.write(KEEPALIVE_COMMAND)
        except usb.core.USBError as e:
            print(f"USB keepalive error: {e}")

    def poll(self):
        try:
            data = self.ep_in.read(64, timeout=1000)
            if data[0] == 0xAA and data[1] == 0x04:
                voltage_uV = int.from_bytes(data[2:6], 'little')
                current_uA = int.from_bytes(data[6:10], 'little')
                dp_mV = int.from_bytes(data[10:12], 'little')
                dn_mV = int.from_bytes(data[12:14], 'little')
                temp_raw = int.from_bytes(data[15:17], 'little')

                voltage = voltage_uV / 100000
                current = current_uA / 100000
                power = voltage * current
                temp_c = temp_raw / 10 if 0 < temp_raw < 1000 else float('nan')

                now = time.time()
                delta_h = (now - self.last_timestamp) / 3600.0
                self.cumulative_mAh += current * 1000 * delta_h
                self.last_timestamp = now

                elapsed_time = now - self.start_time

                data = {
                    'voltage': voltage,
                    'current': current,
                    'power': power,
                    'temperature': temp_c,
                    'dp': dp_mV / 1000,
                    'dn': dn_mV / 1000,
                    'mah': self.cumulative_mAh
                }
                self.csv_writer.writerow([f"{elapsed_time:.2f}", voltage, current, power, temp_c, dp_mV/1000, dn_mV/1000, self.cumulative_mAh])
                self.new_data.emit(data)
        except usb.core.USBError as e:
            print(f"USB poll error: {e}")

    def __del__(self):
        try:
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.close()
            self.run_reporter()
        except Exception as e:
            print(f"Error during cleanup: {e}")


# --- Main Window ---
class PlotterWindow(QtWidgets.QMainWindow):
    def __init__(self, reader):
        super().__init__()
        self.reader = reader
        self.setWindowTitle("USB Meter Dashboard")
        self.resize(1200, 800)

        self.central = QtWidgets.QWidget()
        self.setCentralWidget(self.central)
        self.layout = QtWidgets.QGridLayout()
        self.central.setLayout(self.layout)

        self.plots = {}
        self.curves = {}
        self.smooth_curves = {}
        self.data_buffers = {}
        self.graph_start_time = time.time()

        colors = {
            'Voltage (V)': 'lightblue',
            'Current (A)': 'red',
            'Power (W)': 'orange',
            'Temperature (C)': 'green'
        }

        for i, label in enumerate(['Voltage (V)', 'Current (A)', 'Power (W)', 'Temperature (C)']):
            plot = pg.PlotWidget(title=label)
            plot.showGrid(x=True, y=True)
            plot.setLabel('bottom', 'Time', 's')
            color = colors[label]
            base_color = QColor(color)
            lighter_color = base_color.lighter(155)
            curve = plot.plot(pen=pg.mkPen(color=color, width=1))
            smooth_curve = plot.plot(pen=pg.mkPen(color = lighter_color, width=3))
            plot.setTitle(label, color=color)

            self.plots[label] = plot
            self.curves[label] = curve
            self.smooth_curves[label] = smooth_curve
            self.data_buffers[label] = []

            self.layout.addWidget(plot, i // 2, i % 2)

        self.status_layout = QtWidgets.QHBoxLayout()
        self.dp_label = QtWidgets.QLabel("DP: 0.00 V")
        self.dn_label = QtWidgets.QLabel("DN: 0.00 V")
        self.mah_label = QtWidgets.QLabel("mAh: 0.00")
        self.smoothing_selector = QtWidgets.QComboBox()
        self.smoothing_selector.addItems(["None", "F2", "F4", "F8", "F16"])
        self.smoothing_selector.setCurrentIndex(2)

        self.status_layout.addWidget(self.dp_label)
        self.status_layout.addWidget(self.dn_label)
        self.status_layout.addWidget(self.mah_label)
        self.status_layout.addWidget(self.smoothing_selector)

        self.reset_button = QtWidgets.QPushButton("Reset Session")
        self.reset_button.clicked.connect(self.reset_session)
        self.status_layout.addWidget(self.reset_button)

        self.layout.addLayout(self.status_layout, 2, 0, 1, 2)

    def get_smoothing_window(self):
        selected = self.smoothing_selector.currentText()
        if selected == "None":
            return 1
        else:
            return int(selected[1:])

    def reset_session(self):
        if hasattr(self.reader, 'log_file') and self.reader.log_file:
            self.reader.log_file.close()
            self.reader.run_reporter()

        self.graph_start_time = time.time()
        for buf in self.data_buffers.values():
            buf.clear()
        self.reader.reinitialize()

    def update_plots(self, data):
        timestamp = time.time() - self.graph_start_time

        for key, label in zip(['voltage', 'current', 'power', 'temperature'],
                              ['Voltage (V)', 'Current (A)', 'Power (W)', 'Temperature (C)']):
            buf = self.data_buffers[label]
            buf.append((timestamp, data[key]))
            if len(buf) > 1800:
                buf.pop(0)

            xdata, ydata = zip(*buf)

            # Plot original noisy data
            self.curves[label].setData(x=xdata, y=ydata)
            self.plots[label].enableAutoRange(axis='y')

            # Plot smoothed data
            smooth_window = self.get_smoothing_window()
            if smooth_window > 1 and len(buf) >= smooth_window:
                smooth_ydata = []
                for i in range(len(ydata)):
                    start = max(0, i - smooth_window + 1)
                    smooth_ydata.append(sum(ydata[start:i+1]) / (i-start+1))
                self.smooth_curves[label].setData(x=xdata, y=smooth_ydata)
            else:
                self.smooth_curves[label].clear()

            if key == 'voltage':
                self.plots[label].setTitle(f"Voltage (V): {data[key]:.3f} V")
            elif key == 'current':
                self.plots[label].setTitle(f"Current (A): {data[key]:.3f} A")
            elif key == 'power':
                self.plots[label].setTitle(f"Power (W): {data[key]:.3f} W")
            elif key == 'temperature':
                self.plots[label].setTitle(f"Temperature (C): {data[key]:.3f} C")

        self.dp_label.setText(f"DP: {data['dp']:.2f} V")
        self.dn_label.setText(f"DN: {data['dn']:.2f} V")
        self.mah_label.setText(f"mAh: {data['mah']:.2f}")

# --- Main App Startup ---
def main():
    app = QtWidgets.QApplication(sys.argv)

    reader = USBMeterReader()
    window = PlotterWindow(reader)

    reader.new_data.connect(window.update_plots)
    reader.start()

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
