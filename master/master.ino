#include <Arduino.h>
#include <SoftwareSerial.h>
SoftwareSerial rs485(2, 3); // RX=2, TX=3

// ===== KONFIGURASI NODE =====
#define SLAVE_SENSOR_ADDR    0x24
#define SLAVE_AKTUATOR_ADDR  0x66

// ===== PERINTAH DARI PYTHON GUI =====
#define CMD_READ_ULTRASONIC  'U'
#define CMD_READ_TCRT        'T'
#define CMD_CONTROL_RELAY    'R'

// ===== FUNCTION CODE MODBUS =====
#define FC_READ_ULTRASONIC   0x01
#define FC_READ_TCRT5000     0x02
#define FC_CONTROL_RELAY     0x03

// ===== TIMEOUT =====
#define RESPONSE_TIMEOUT     200  // Timeout lebih panjang untuk modul TX/RX

void setup() {
  Serial.begin(9600);
  rs485.begin(9600);
  
  // Flush buffer awal
  while(rs485.available()) rs485.read();
  while(Serial.available()) Serial.read();
}

void loop() {
  if (Serial.available() > 0) {
    uint8_t inByte = Serial.read();
    
    if (inByte == CMD_READ_ULTRASONIC) {
      requestSensorData(SLAVE_SENSOR_ADDR, FC_READ_ULTRASONIC);
      
    } else if (inByte == CMD_READ_TCRT) {
      requestSensorData(SLAVE_SENSOR_ADDR, FC_READ_TCRT5000);
      
    } else if (inByte == CMD_CONTROL_RELAY) {
      // Tunggu byte berikutnya untuk relay command
      unsigned long waitStart = millis();
      while (!Serial.available() && (millis() - waitStart) < 100);
      
      if (Serial.available() > 0) {
        uint8_t relayCmd = Serial.read();
        controlRelay(relayCmd);
      }
    }
  }
}

// ===== REQUEST DATA SENSOR =====
void requestSensorData(uint8_t slaveAddr, uint8_t functionCode) {
  // Clear RX buffer sebelum kirim
  while(rs485.available()) rs485.read();
  
  // Siapkan paket request
  uint8_t request[5];
  request[0] = slaveAddr;
  request[1] = functionCode;
  request[2] = 0x00;
  
  uint16_t crc = calculateCRC(request, 3);
  request[3] = crc & 0xFF;
  request[4] = (crc >> 8) & 0xFF;
  
  // Kirim request
  rs485.write(request, 5);
  rs485.flush();  // PENTING: Tunggu transmisi selesai
  
  // Delay untuk switching dan processing
  delay(20);
  
  // Baca response
  uint8_t response[5];
  uint8_t idx = 0;
  unsigned long timeout = millis();
  
  while (idx < 5 && (millis() - timeout) < RESPONSE_TIMEOUT) {
    if (rs485.available() > 0) {
      response[idx++] = rs485.read();
      timeout = millis(); // Reset timeout setiap byte diterima
    }
  }
  
  // Validasi response
  if (idx == 5) {
    uint16_t receivedCRC = (response[4] << 8) | response[3];
    uint16_t calculatedCRC = calculateCRC(response, 3);
    
    if (receivedCRC == calculatedCRC && response[0] == slaveAddr) {
      // Kirim ke Python: [ADDR][FC][DATA]
      Serial.write(response, 3);
    } else {
      // Debug: kirim error indicator
      Serial.write(0xFF); // Error byte
      Serial.write(0xE1); // CRC error
    }
  } else {
    // Debug: timeout
    Serial.write(0xFF);
    Serial.write(0xE2); // Timeout error
  }
}

// ===== KONTROL RELAY =====
void controlRelay(uint8_t command) {
  // Clear RX buffer
  while(rs485.available()) rs485.read();
  
  // Siapkan paket request
  uint8_t request[5];
  request[0] = SLAVE_AKTUATOR_ADDR;
  request[1] = FC_CONTROL_RELAY;
  request[2] = command;
  
  uint16_t crc = calculateCRC(request, 3);
  request[3] = crc & 0xFF;
  request[4] = (crc >> 8) & 0xFF;
  
  // Kirim request
  rs485.write(request, 5);
  rs485.flush();
  
  // Delay untuk switching dan processing
  delay(20);
  
  // Baca response
  uint8_t response[5];
  uint8_t idx = 0;
  unsigned long timeout = millis();
  
  while (idx < 5 && (millis() - timeout) < RESPONSE_TIMEOUT) {
    if (rs485.available() > 0) {
      response[idx++] = rs485.read();
      timeout = millis();
    }
  }
  
  // Validasi response
  if (idx == 5) {
    uint16_t receivedCRC = (response[4] << 8) | response[3];
    uint16_t calculatedCRC = calculateCRC(response, 3);
    
    if (receivedCRC == calculatedCRC && response[0] == SLAVE_AKTUATOR_ADDR) {
      Serial.write(response, 3);
    } else {
      Serial.write(0xFF);
      Serial.write(0xE1);
    }
  } else {
    Serial.write(0xFF);
    Serial.write(0xE2);
  }
}

// ===== CRC16 MODBUS =====
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