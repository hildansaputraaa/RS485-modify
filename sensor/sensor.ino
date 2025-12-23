#include <Arduino.h>
#include <SoftwareSerial.h>
SoftwareSerial rs485(2, 3); // RX, TX

// ===== KONFIGURASI NODE =====
#define SLAVE_ADDRESS 0x24

// ===== PIN SENSOR =====
// Sensor Ultrasonik HC-SR04
#define TRIG_PIN 13
#define ECHO_PIN 12

// Sensor TCRT5000 (IR Line Follow  er)
#define TCRT_PIN A0
#define TCRT_THRESHOLD 512  // Threshold untuk deteksi hitam/putih

// ===== BUFFER KOMUNIKASI =====
uint8_t rxBuffer[10];
uint8_t rxIndex = 0;
unsigned long lastByteTime = 0;

// ===== FUNCTION CODE MODBUS =====
#define FC_READ_ULTRASONIC   0x01
#define FC_READ_TCRT5000     0x02
#define FC_CONTROL_RELAY     0x03

void setup() {
  rs485.begin(9600);
  Serial.begin(9600);
  // Setup pin Ultrasonik
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  // Setup pin TCRT5000
  pinMode(TCRT_PIN, INPUT);
}

void loop() {
  // Reset buffer jika timeout (3.5 karakter @ 9600bps ≈ 4ms)
  if (rxIndex > 0 && (millis() - lastByteTime) > 5) {
    rxIndex = 0;
  }
  
  // Terima data rs485
  if (rs485.available() > 0) {
    uint8_t inByte = rs485.read();
    lastByteTime = millis();
    rxBuffer[rxIndex++] = inByte;
    
    // Proses paket jika sudah 5 byte: [ADDR][FC][DATA][CRC_L][CRC_H]
    if (rxIndex >= 5) {
      processModbusPacket();
      rxIndex = 0;
    }
    
    // Reset jika buffer penuh
    if (rxIndex >= 10) {
      rxIndex = 0;
    }
  }
}

// ===== PROSES PAKET MODBUS =====
void processModbusPacket() {
  uint8_t deviceAddr = rxBuffer[0];
  uint8_t functionCode = rxBuffer[1];
  
  // Cek alamat device
  if (deviceAddr != SLAVE_ADDRESS) {
    return;
  }
  
  // Verifikasi CRC
  uint16_t receivedCRC = (rxBuffer[4] << 8) | rxBuffer[3];
  uint16_t calculatedCRC = calculateCRC(rxBuffer, 3);
  
  if (receivedCRC != calculatedCRC) {
    return;  // CRC tidak valid, abaikan paket
  }
  
  // Proses berdasarkan function code
  if (functionCode == FC_READ_ULTRASONIC) {
    // Baca sensor Ultrasonik
    uint8_t distance = readUltrasonic();
    sendResponse(distance);
    
  } else if (functionCode == FC_READ_TCRT5000) {
    // Baca sensor TCRT5000
    uint8_t tcrtStatus = readTCRT5000();
    sendResponse(tcrtStatus);
  }
}

// ===== BACA SENSOR ULTRASONIK =====
uint8_t readUltrasonic() {
  // Kirim trigger pulse
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Baca echo dan hitung jarak
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);  // Timeout 30ms
  uint8_t distance = duration * 0.034 / 2;  // Konversi ke cm
  
  // Batasi range 0-255
  if (distance > 255) distance = 255;
  // Serial.print(distance);
  return distance;
}

// ===== BACA SENSOR TCRT5000 =====
uint8_t readTCRT5000() {
  int analogValue = analogRead(TCRT_PIN);
  
  // Return 1 jika terdeteksi (gelap/hitam), 0 jika tidak (terang/putih)
  if (analogValue < TCRT_THRESHOLD) {
    return 0x01;  // Objek/garis terdeteksi
  } else {
    return 0x00;  // Tidak terdeteksi
  }
  // Serial.print(analogValue);
}

// ===== KIRIM RESPONSE =====
void sendResponse(uint8_t sensorData) {
  // Siapkan paket response 5 byte
  uint8_t response[5];
  response[0] = SLAVE_ADDRESS;           // Byte 0: Alamat slave
  response[1] = rxBuffer[1];             // Byte 1: Function code (echo dari request)
  response[2] = sensorData;              // Byte 2: Data sensor
  
  // Hitung CRC16 Modbus
  uint16_t crc = calculateCRC(response, 3);
  response[3] = crc & 0xFF;              // Byte 3: CRC Low
  response[4] = (crc >> 8) & 0xFF;       // Byte 4: CRC High
  
  // Kirim response via rs485
  rs485.write(response, 5);
  rs485.flush();
}

// ===== HITUNG CRC16 MODBUS =====
uint16_t calculateCRC(uint8_t *buf, uint8_t len) {
  uint16_t crc = 0xFFFF;
  
  for (uint8_t pos = 0; pos < len; pos++) {
    crc ^= (uint16_t)buf[pos];
    
    for (uint8_t i = 8; i != 0; i--) {
      if ((crc & 0x0001) != 0) {
        crc >>= 1;
        crc ^= 0xA001;
      } else {
        crc >>= 1;
      }
    }
  }
  
  return crc;
}