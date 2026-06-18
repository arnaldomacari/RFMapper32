/*
 * Projeto: Transmissor LoRa
 * Plataforma: ESP32-C3 Super Mine
 * Autor: Arnaldo José Macari
 * Data: 2026-06-14
 * Licença: MIT
 */

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// =====================
// OLED SSD1306
// =====================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_ADDR 0x3C

#define OLED_SDA 8
#define OLED_SCL 9

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// =====================
// LoRa RA-01
// =====================
const int csPin = 7;
const int resetPin = 3;
const int irqPin = 10;

byte msgCount = 0;
int interval = 2000;
long lastSendTime = 0;

String lastMessage = "";

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("LoRa Duplex - Set spreading factor");

  // OLED
  Wire.begin(OLED_SDA, OLED_SCL);

  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("Erro ao iniciar OLED SSD1306");
    while (true);
  }
  display.setRotation(2);
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("LoRa TX");
  display.println("Iniciando...");
  display.display();

  // LoRa
  LoRa.setPins(csPin, resetPin, irqPin);

  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed. Check your connections.");

    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("Erro LoRa!");
    display.println("Verifique fios.");
    display.display();

    delay(1000);
    while (true);
  }

  LoRa.setSpreadingFactor(8);

  Serial.println("LoRa init succeeded.");

  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("LoRa iniciado!");
  display.println("Freq: 433 MHz");
  display.println("SF: 8");
  display.display();

  delay(1000);
}

void loop() {
  if (millis() - lastSendTime > interval) {
    String message = "Olora Mundo! ";
    message += msgCount;

    sendMessage(message);

    Serial.println("Sending " + message);

    lastMessage = message;
    showTxMessage(message, msgCount);

    lastSendTime = millis();
    interval = random(2000) + 1000;
    msgCount++;
  }

}

void sendMessage(String outgoing) {
  LoRa.beginPacket();
  LoRa.print(outgoing);
  LoRa.endPacket();
}



void showTxMessage(String message, byte count) {
  display.clearDisplay();

  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("LoRa TRANSMITINDO");

  display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

  display.setCursor(0, 16);
  display.print("Contador: ");
  display.println(count);

  display.setCursor(0, 30);
  display.println("Mensagem:");

  display.setCursor(0, 42);
  display.println(message);

  display.display();
}



/*
#include <SPI.h>              
#include <LoRa.h>

const int csPin = 7;         
const int resetPin = 3;       
const int irqPin = 10;        

byte msgCount = 0;            
int interval = 2000;          
long lastSendTime = 0;        

void setup() {
  Serial.begin(115200);                  
  while (!Serial);
  delay(1000);

  Serial.println("LoRa Duplex - Set spreading factor");

  LoRa.setPins(csPin, resetPin, irqPin); 

  if (!LoRa.begin(433E6)) {             
    Serial.println("LoRa init failed. Check your connections.");
    delay(1000);
    while (true);                       
  }

  LoRa.setSpreadingFactor(8);          
  Serial.println("LoRa init succeeded.");
}

void loop() {
  if (millis() - lastSendTime > interval) {
    String message = "Olora Mundo! ";   
    message += msgCount;
    sendMessage(message);
    Serial.println("Sending " + message);
    lastSendTime = millis();           
    interval = random(2000) + 1000;    
    msgCount++;
  }

  onReceive(LoRa.parsePacket());
}

void sendMessage(String outgoing) {
  LoRa.beginPacket();                   
  LoRa.print(outgoing);                 
  LoRa.endPacket();                                             
}

void onReceive(int packetSize) {
  if (packetSize == 0) return;          
 
  String incoming = "";

  while (LoRa.available()) {
    incoming += (char)LoRa.read();
  }

  Serial.println("Message: " + incoming);
  Serial.println("RSSI: " + String(LoRa.packetRssi()));
  Serial.println("Snr: " + String(LoRa.packetSnr()));
  Serial.println();
}
*/
