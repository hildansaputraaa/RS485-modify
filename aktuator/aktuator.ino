#include <Arduino.h>
#include <SoftwareSerial.h>
SoftwareSerial rs485(2, 3); // RX=2, TX=3

// ===== KONFIGURASI NODE =====
#define SLAVE_ADDRESS 0x66

// ===== PIN AKTUATOR =====
#define RELAY_PIN 4

// ===== BUFFER KOMUNIKASI =====
uint8_t rxBuffer[10];
uint8_t rxIndex = 0;
unsigned long lastByteTime = 0;

// ===== STATUS RELAY =====
uint8_t relayStatus = 0x00;  // 0x00 = OFF, 0x01 = ON

// ===== FUNCTION CODE MODBUS =====
#define FC_CONTROL_RELAY 0x03

// ===== PERINTAH RELAY =====
#define CMD_RELAY_OFF 0x00
#define CMD_RELAY_ON  0x01

void setup() {
  rs485.begin(9600);
  
  // Setup pin Relay
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);  // Relay OFF pada awal
  relayStatus = 0x00;
  
  // Flush buffer awal
  while(rs485.available()) rs485.read();
}

void loop() {
  // Reset buffer jika timeout (10ms untuk 9600bps)
  if (rxIndex > 0 && (millis() - lastByteTime) > 10) {
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
    
    // Reset jika buffer penuh (proteksi)
    if (rxIndex >= 10) {
      rxIndex = 0;
    }
  }
}

// ===== PROSES PAKET MODBUS =====
void processModbusPacket() {
  uint8_t deviceAddr = rxBuffer[0];
  uint8_t functionCode = rxBuffer[1];
  uint8_t data = rxBuffer[2];
  
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
  if (functionCode == FC_CONTROL_RELAY) {
    // Kontrol Relay ON/OFF
    controlRelay(data);
    
    // Delay kecil sebelum kirim response (beri waktu master switch ke RX)
    delay(5);
    
    sendResponse(relayStatus);
  }
}

// ===== KONTROL RELAY =====
void controlRelay(uint8_t command) {
  if (command == CMD_RELAY_OFF) {
    // Matikan Relay
    digitalWrite(RELAY_PIN, LOW);
    relayStatus = 0x00;
    
  } else if (command == CMD_RELAY_ON) {
    // Nyalakan Relay
    digitalWrite(RELAY_PIN, HIGH);
    relayStatus = 0x01;
  }
}

// ===== KIRIM RESPONSE =====
void sendResponse(uint8_t statusData) {
  // Siapkan paket response 5 byte
  uint8_t response[5];
  response[0] = SLAVE_ADDRESS;           // Byte 0: Alamat slave
  response[1] = FC_CONTROL_RELAY;        // Byte 1: Function code
  response[2] = statusData;              // Byte 2: Status relay (0x00=OFF, 0x01=ON)
  
  // Hitung CRC16 Modbus
  uint16_t crc = calculateCRC(response, 3);
  response[3] = crc & 0xFF;              // Byte 3: CRC Low
  response[4] = (crc >> 8) & 0xFF;       // Byte 4: CRC High
  
  // Kirim response via rs485
  rs485.write(response, 5);
  rs485.flush();  // PENTING: Tunggu transmisi selesai
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