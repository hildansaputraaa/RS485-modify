import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QGroupBox, QTextEdit, QCheckBox, QFrame)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
import serial
import serial.tools.list_ports
import time

class ModbusGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modbus RTU Master Control - Project Elektronika Industri")
        self.setGeometry(100, 100, 900, 700)
        
        # Variables
        self.serial_port = None
        self.is_connected = False
        self.auto_read_timer = None
        
        # Setup UI
        self.init_ui()
        self.refresh_ports()
        
        # Apply dark theme
        self.apply_dark_theme()
    
    def init_ui(self):
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # ===== CONNECTION FRAME =====
        conn_frame = self.create_connection_frame()
        main_layout.addWidget(conn_frame)
        
        # ===== SENSOR FRAME =====
        sensor_frame = self.create_sensor_frame()
        main_layout.addWidget(sensor_frame)
        
        # ===== ACTUATOR FRAME =====
        actuator_frame = self.create_actuator_frame()
        main_layout.addWidget(actuator_frame)
        
        # ===== LOG FRAME =====
        log_frame = self.create_log_frame()
        main_layout.addWidget(log_frame)
    
    def create_connection_frame(self):
        """Frame untuk koneksi serial"""
        group = QGroupBox("🔌 Serial Connection")
        group.setFont(QFont("Arial", 11, QFont.Bold))
        layout = QHBoxLayout()
        
        # Port Label
        port_label = QLabel("Port:")
        port_label.setFont(QFont("Arial", 10))
        layout.addWidget(port_label)
        
        # Port ComboBox
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(200)
        layout.addWidget(self.port_combo)
        
        # Refresh Button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self.refresh_ports)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        layout.addWidget(refresh_btn)
        
        # Connect Button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setFixedWidth(120)
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        layout.addWidget(self.connect_btn)
        
        # Status Label
        self.status_label = QLabel("● Disconnected")
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.status_label.setStyleSheet("color: #e74c3c;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_sensor_frame(self):
        """Frame untuk slave sensor"""
        group = QGroupBox("📡 Slave Sensor (0x24)")
        group.setFont(QFont("Arial", 12, QFont.Bold))
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # === ULTRASONIK ===
        ultra_layout = QHBoxLayout()
        
        ultra_label = QLabel("Sensor Ultrasonik:")
        ultra_label.setFont(QFont("Arial", 11, QFont.Bold))
        ultra_layout.addWidget(ultra_label)
        
        self.ultra_btn = QPushButton("Read Distance")
        self.ultra_btn.setFixedWidth(150)
        self.ultra_btn.clicked.connect(self.read_ultrasonic)
        self.ultra_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        ultra_layout.addWidget(self.ultra_btn)
        
        self.ultra_value = QLabel("-- cm")
        self.ultra_value.setFont(QFont("Arial", 18, QFont.Bold))
        self.ultra_value.setAlignment(Qt.AlignCenter)
        self.ultra_value.setFixedWidth(150)
        self.ultra_value.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                color: #1abc9c;
                border: 2px solid #34495e;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        ultra_layout.addWidget(self.ultra_value)
        ultra_layout.addStretch()
        
        layout.addLayout(ultra_layout)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # === TCRT5000 ===
        tcrt_layout = QHBoxLayout()
        
        tcrt_label = QLabel("Sensor TCRT5000:")
        tcrt_label.setFont(QFont("Arial", 11, QFont.Bold))
        tcrt_layout.addWidget(tcrt_label)
        
        self.tcrt_btn = QPushButton("Read Status")
        self.tcrt_btn.setFixedWidth(150)
        self.tcrt_btn.clicked.connect(self.read_tcrt)
        self.tcrt_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        tcrt_layout.addWidget(self.tcrt_btn)
        
        self.tcrt_value = QLabel("NO OBJECT")
        self.tcrt_value.setFont(QFont("Arial", 16, QFont.Bold))
        self.tcrt_value.setAlignment(Qt.AlignCenter)
        self.tcrt_value.setFixedWidth(180)
        self.tcrt_value.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                color: #95a5a6;
                border: 2px solid #34495e;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        tcrt_layout.addWidget(self.tcrt_value)
        tcrt_layout.addStretch()
        
        layout.addLayout(tcrt_layout)
        
        # Auto Read Checkbox
        self.auto_read_check = QCheckBox("Auto Read (1s interval)")
        self.auto_read_check.setFont(QFont("Arial", 10))
        self.auto_read_check.stateChanged.connect(self.toggle_auto_read)
        layout.addWidget(self.auto_read_check)
        
        group.setLayout(layout)
        return group
    
    def create_actuator_frame(self):
        """Frame untuk slave aktuator"""
        group = QGroupBox("🔌 Slave Aktuator (0x66)")
        group.setFont(QFont("Arial", 12, QFont.Bold))
        layout = QHBoxLayout()
        
        relay_label = QLabel("Relay Control:")
        relay_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(relay_label)
        
        # ON Button
        self.relay_on_btn = QPushButton("ON")
        self.relay_on_btn.setFixedSize(120, 60)
        self.relay_on_btn.clicked.connect(lambda: self.control_relay(1))
        self.relay_on_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        layout.addWidget(self.relay_on_btn)
        
        # OFF Button
        self.relay_off_btn = QPushButton("OFF")
        self.relay_off_btn.setFixedSize(120, 60)
        self.relay_off_btn.clicked.connect(lambda: self.control_relay(0))
        self.relay_off_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        layout.addWidget(self.relay_off_btn)
        
        # Status Label
        self.relay_status = QLabel("OFF")
        self.relay_status.setFont(QFont("Arial", 18, QFont.Bold))
        self.relay_status.setAlignment(Qt.AlignCenter)
        self.relay_status.setFixedWidth(120)
        self.relay_status.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                color: #e74c3c;
                border: 2px solid #34495e;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.relay_status)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_log_frame(self):
        """Frame untuk log komunikasi"""
        group = QGroupBox("📋 Communication Log")
        group.setFont(QFont("Arial", 11, QFont.Bold))
        layout = QVBoxLayout()
        
        # Log Text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff00;
                border: 2px solid #34495e;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # Clear Button
        clear_btn = QPushButton("Clear Log")
        clear_btn.setFixedWidth(100)
        clear_btn.clicked.connect(self.clear_log)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        layout.addWidget(clear_btn)
        
        group.setLayout(layout)
        return group
    
    def apply_dark_theme(self):
        """Apply dark theme to application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2c3e50;
            }
            QGroupBox {
                background-color: #34495e;
                border: 2px solid #4a5f7f;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 15px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: white;
            }
            QLabel {
                color: white;
            }
            QCheckBox {
                color: white;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QComboBox {
                background-color: #2c3e50;
                color: white;
                border: 2px solid #34495e;
                border-radius: 4px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2c3e50;
                color: white;
                selection-background-color: #3498db;
            }
        """)
    
    def refresh_ports(self):
        """Refresh daftar port serial"""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)
        
        if self.port_combo.count() == 0:
            self.log("⚠️ No serial ports found!")
    
    def toggle_connection(self):
        """Toggle koneksi serial"""
        if not self.is_connected:
            port = self.port_combo.currentText()
            if not port:
                self.log("❌ Error: No port selected!")
                return
            
            try:
                self.serial_port = serial.Serial(port, 9600, timeout=0.5)
                time.sleep(2)  # Tunggu Arduino reset
                
                # Flush buffer awal
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
                
                self.is_connected = True
                self.connect_btn.setText("Disconnect")
                self.connect_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: white;
                        border: none;
                        padding: 8px;
                        border-radius: 4px;
                        font-size: 11pt;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #c0392b;
                    }
                """)
                self.status_label.setText("● Connected")
                self.status_label.setStyleSheet("color: #27ae60;")
                self.log(f"✅ Connected to {port}")
                
            except Exception as e:
                self.log(f"❌ Connection failed: {str(e)}")
        else:
            if self.serial_port:
                self.serial_port.close()
            
            self.is_connected = False
            self.auto_read_check.setChecked(False)
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-size: 11pt;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.log("🔌 Disconnected")
    
    def read_ultrasonic(self):
        """Baca sensor ultrasonik"""
        if not self.is_connected:
            self.log("❌ Not connected!")
            return
        
        try:
            # Flush buffer sebelum kirim
            self.serial_port.reset_input_buffer()
            
            # Kirim perintah
            self.serial_port.write(b'U')
            
            # Tunggu response (timeout 500ms)
            start_time = time.time()
            while self.serial_port.in_waiting < 3:
                if time.time() - start_time > 0.5:
                    self.log("⏱️ Timeout: No response from sensor")
                    return
                time.sleep(0.01)
            
            # Baca response
            data = self.serial_port.read(3)
            
            # Cek error byte
            if data[0] == 0xFF:
                if data[1] == 0xE1:
                    self.log("❌ Error: CRC mismatch")
                elif data[1] == 0xE2:
                    self.log("❌ Error: Slave timeout")
                return
            
            addr, fc, value = data[0], data[1], data[2]
            
            if addr == 0x24 and fc == 0x01:
                self.ultra_value.setText(f"{value} cm")
                self.log(f"📏 Ultrasonic: {value} cm [0x{addr:02X}][0x{fc:02X}][0x{value:02X}]")
            else:
                self.log(f"⚠️ Invalid response: [0x{addr:02X}][0x{fc:02X}][0x{value:02X}]")
                
        except Exception as e:
            self.log(f"❌ Read error: {str(e)}")
    
    def read_tcrt(self):
        """Baca sensor TCRT5000"""
        if not self.is_connected:
            self.log("❌ Not connected!")
            return
        
        try:
            # Flush buffer sebelum kirim
            self.serial_port.reset_input_buffer()
            
            # Kirim perintah
            self.serial_port.write(b'T')
            
            # Tunggu response
            start_time = time.time()
            while self.serial_port.in_waiting < 3:
                if time.time() - start_time > 0.5:
                    self.log("⏱️ Timeout: No response from sensor")
                    return
                time.sleep(0.01)
            
            # Baca response
            data = self.serial_port.read(3)
            
            # Cek error byte
            if data[0] == 0xFF:
                if data[1] == 0xE1:
                    self.log("❌ Error: CRC mismatch")
                elif data[1] == 0xE2:
                    self.log("❌ Error: Slave timeout")
                return
            
            addr, fc, value = data[0], data[1], data[2]
            
            if addr == 0x24 and fc == 0x02:
                if value == 0x01:
                    self.tcrt_value.setText("DETECTED")
                    self.tcrt_value.setStyleSheet("""
                        QLabel {
                            background-color: #2c3e50;
                            color: #e74c3c;
                            border: 2px solid #34495e;
                            border-radius: 4px;
                            padding: 10px;
                        }
                    """)
                    self.log(f"🔴 TCRT: Object DETECTED [0x{addr:02X}][0x{fc:02X}][0x{value:02X}]")
                else:
                    self.tcrt_value.setText("NO OBJECT")
                    self.tcrt_value.setStyleSheet("""
                        QLabel {
                            background-color: #2c3e50;
                            color: #95a5a6;
                            border: 2px solid #34495e;
                            border-radius: 4px;
                            padding: 10px;
                        }
                    """)
                    self.log(f"⚪ TCRT: No object [0x{addr:02X}][0x{fc:02X}][0x{value:02X}]")
            else:
                self.log(f"⚠️ Invalid response: [0x{addr:02X}][0x{fc:02X}][0x{value:02X}]")
                
        except Exception as e:
            self.log(f"❌ Read error: {str(e)}")
    
    def control_relay(self, state):
        """Kontrol relay ON/OFF"""
        if not self.is_connected:
            self.log("❌ Not connected!")
            return
        
        try:
            # Flush buffer sebelum kirim
            self.serial_port.reset_input_buffer()
            
            # Kirim perintah
            cmd = b'R' + bytes([state])
            self.serial_port.write(cmd)
            
            # Tunggu response
            start_time = time.time()
            while self.serial_port.in_waiting < 3:
                if time.time() - start_time > 0.5:
                    self.log("⏱️ Timeout: No response from actuator")
                    return
                time.sleep(0.01)
            
            # Baca response
            data = self.serial_port.read(3)
            
            # Cek error byte
            if data[0] == 0xFF:
                if data[1] == 0xE1:
                    self.log("❌ Error: CRC mismatch")
                elif data[1] == 0xE2:
                    self.log("❌ Error: Slave timeout")
                return
            
            addr, fc, value = data[0], data[1], data[2]
            
            # FIX: Function code untuk relay adalah 0x03, bukan 0x01
            if addr == 0x66 and fc == 0x03:
                if value == 0x01:
                    self.relay_status.setText("ON")
                    self.relay_status.setStyleSheet("""
                        QLabel {
                            background-color: #2c3e50;
                            color: #27ae60;
                            border: 2px solid #34495e;
                            border-radius: 4px;
                            padding: 10px;
                        }
                    """)
                    self.log(f"✅ Relay: ON [0x{addr:02X}][0x{fc:02X}][0x{value:02X}]")
                else:
                    self.relay_status.setText("OFF")
                    self.relay_status.setStyleSheet("""
                        QLabel {
                            background-color: #2c3e50;
                            color: #e74c3c;
                            border: 2px solid #34495e;
                            border-radius: 4px;
                            padding: 10px;
                        }
                    """)
                    self.log(f"⛔ Relay: OFF [0x{addr:02X}][0x{fc:02X}][0x{value:02X}]")
            else:
                self.log(f"⚠️ Invalid response: [0x{addr:02X}][0x{fc:02X}][0x{value:02X}]")
                
        except Exception as e:
            self.log(f"❌ Control error: {str(e)}")
    
    def toggle_auto_read(self, state):
        """Toggle auto read sensor"""
        if state == Qt.Checked:
            if not self.is_connected:
                self.auto_read_check.setChecked(False)
                self.log("❌ Connect first before enabling auto read!")
                return
            
            self.log("🔄 Auto read enabled")
            self.auto_read_timer = QTimer()
            self.auto_read_timer.timeout.connect(self.auto_read_sensors)
            self.auto_read_timer.start(1000)  # Every 1 second
        else:
            if self.auto_read_timer:
                self.auto_read_timer.stop()
                self.auto_read_timer = None
            self.log("⏸️ Auto read disabled")
    
    def auto_read_sensors(self):
        """Auto read kedua sensor"""
        self.read_ultrasonic()
        QTimer.singleShot(500, self.read_tcrt)  # Delay 500ms untuk TCRT
    
    def log(self, message):
        """Tambah pesan ke log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Auto scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def clear_log(self):
        """Bersihkan log"""
        self.log_text.clear()
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.is_connected and self.serial_port:
            self.serial_port.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModbusGUI()
    window.show()
    sys.exit(app.exec_())