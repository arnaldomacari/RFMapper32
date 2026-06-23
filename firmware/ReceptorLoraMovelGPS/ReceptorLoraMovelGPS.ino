/**
 * Projeto: Receptor LoRa + GPS + Gravação em SD + OLED + WiFi RSSI (passivo)
 * Plataforma: ESP32 DevKit V1
 * Autor: Arnaldo José Macari
 * Data: 2026-06-14
 * Licença: MIT
 */

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <TinyGPSPlus.h>
#include <SD.h>
#include <WiFi.h>

// --------------------- GPS ---------------------
TinyGPSPlus gps;
#define GPS_RX_PIN 36
#define GPS_BAUD 9600

// --------------------- OLED ---------------------
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --------------------- LoRa (VSPI) ---------------------
#define LORA_CS_PIN 5
#define LORA_RST_PIN 32
#define LORA_IRQ_PIN 4  // IO0

// --------------------- SD Card (HSPI) ---------------------
#define SD_CS_PIN 15
SPIClass *hspi = nullptr;

File dataFile;
bool sdInitialized = false;
bool fileCreated = false;
String filename = "";
String wifiData = "";

// --------------------- Variáveis ---------------------
unsigned long lastDisplayUpdate = 0;
const unsigned long displayInterval = 1000;  // Atualiza a cada 1s

String lastLoRaMessage = "";
int lastLoRaRSSI = 0;
float lastLoRaSNR = 0;

// --------------------- Wi-Fi Passivo ---------------------
String strongestWiFiSSID = "N/A";
int strongestWiFiRSSI = 0;
int strongestWiFiChannel = 0;

// --------------------- Função para formatar data/hora do GPS (fuso -3) ---------------------
String getFormattedDateTime() {
  if (!gps.date.isValid() || !gps.time.isValid()) return "";

  int year = gps.date.year();
  int month = gps.date.month();
  int day = gps.date.day();
  int hour = gps.time.hour();
  int minute = gps.time.minute();
  int second = gps.time.second();

  //Aplica fuso horário -3
  hour -= 3;
  if (hour < 0) {
    hour += 24;
    day--;
    if (day < 1) {
      month--;
      if (month < 1) {
        month = 12;
        year--;
      }
      day = 31;  // Ajuste aproximado
    }
  }

  String dateTime = "";
  dateTime += (year < 10 ? "0" : "") + String(year % 100, DEC);
  dateTime += (month < 10 ? "0" : "") + String(month, DEC);
  dateTime += (day < 10 ? "0" : "") + String(day, DEC);
  dateTime += "_";
  dateTime += (hour < 10 ? "0" : "") + String(hour, DEC);
  dateTime += (minute < 10 ? "0" : "") + String(minute, DEC);
  dateTime += (second < 10 ? "0" : "") + String(second, DEC);

  Serial.print("data e hora");
  Serial.println(dateTime);
  return dateTime;
}

// --------------------- Função para criar nome do arquivo ---------------------
String generateFilename() {
  String dt = getFormattedDateTime();
  if (dt == "") {
    Serial.println("Data/hora GPS ainda não válida.");
    //return "";  // ou retorne um nome padrão para debug
  }
  return "/gps_" + dt + ".csv";
}

// --------------------- Função para salvar dados no SD ---------------------
void saveDataToSD() {
  if (!sdInitialized) {
    Serial.println("⚠️ SD não inicializado.");
    return;
  }

  if (!gps.location.isValid()) {
    Serial.println("⚠️ GPS sem localização válida.");
    return;
  }

  if (!gps.date.isValid() || !gps.time.isValid()) {
    Serial.println("⏳ GPS ainda sem data/hora válida — aguardando fix...");
    Serial.print("🛰️ Satélites: ");
    Serial.println(gps.satellites.value());
    return;
  }

  if (!fileCreated) {
    filename = generateFilename();
    if (filename == "") {
      Serial.println("❌ Nome de arquivo vazio — verifique geração de data/hora.");
      return;
    }

    Serial.print("📁 Tentando criar: ");
    Serial.println(filename);

    // ✅ ESTILO DO EXEMPLO: testa SE FALHOU
    dataFile = SD.open(filename, FILE_WRITE);
    if (!dataFile) {
      Serial.println("❌ Falha ao abrir arquivo para escrita!");
      return;
    }

    // ✅ Se chegou aqui, arquivo foi aberto com sucesso
    dataFile.println("Data Hora,Latitude,Longitude,nSatelites,HDOP,RSSI-LORA,SNR-LORA,nWIFI,RSSI-WIFI,SSID-WIFI");
    dataFile.close();
    fileCreated = true;
    Serial.println("✅ Arquivo criado com sucesso!");
  }

  // --- Escreve os dados ---
  dataFile = SD.open(filename, FILE_APPEND);
  if (!dataFile) {
    Serial.println("❌ Falha ao abrir arquivo para APPEND!");
    return;
  }

  // Formata timestamp com fuso -3
  int hour = gps.time.hour() - 3;
  int day = gps.date.day();
  int month = gps.date.month();
  int year = gps.date.year();

  if (hour < 0) {
    hour += 24;
    day--;
    if (day < 1) {
      month--;
      if (month < 1) {
        month = 12;
        year--;
      }
      day = 31;
    }
  }

  String ts = String(year) + "-" + (month < 10 ? "0" : "") + String(month) + "-" + (day < 10 ? "0" : "") + String(day) + " " + (hour < 10 ? "0" : "") + String(hour) + ":" + (gps.time.minute() < 10 ? "0" : "") + String(gps.time.minute()) + ":" + (gps.time.second() < 10 ? "0" : "") + String(gps.time.second());

  dataFile.print(ts);
  dataFile.print(",");
  dataFile.print(gps.location.lat(), 7);
  dataFile.print(",");
  dataFile.print(gps.location.lng(), 7);
  dataFile.print(",");
  dataFile.print(gps.satellites.value());
  dataFile.print(",");
  dataFile.print(gps.hdop.hdop(), 1);
  dataFile.print(",");
  dataFile.print(lastLoRaRSSI);
  dataFile.print(",");
  dataFile.print(lastLoRaSNR, 1);
  dataFile.print(",");
  dataFile.println(wifiData);
  dataFile.close();
  Serial.println("💾 Dados salvos com sucesso!");
}



// --------------------- Função para escanear Wi-Fi passivamente ---------------------
void scanWiFiPassive() {
  // Desativa Wi-Fi se estiver ligado
  digitalWrite(LED_BUILTIN, HIGH);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  // Escaneia redes no modo PASSIVO (não transmite nada!)
  int n = WiFi.scanNetworks(false, true);
  strongestWiFiRSSI = -100;  // valor inicial baixo
  strongestWiFiSSID = "N/A";
  wifiData = String(n);
  if (n > 0) {
    for (int i = 0; i < n; i++) {
      int rssi = WiFi.RSSI(i);
        strongestWiFiRSSI = rssi;
        strongestWiFiSSID = WiFi.SSID(i).c_str();
        wifiData += ",";
        wifiData += String(strongestWiFiSSID);
        wifiData += ",";
        wifiData += String(strongestWiFiRSSI);      
    }
  }
  WiFi.scanDelete();  // Libera memória
  digitalWrite(LED_BUILTIN, LOW);
}


void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("Iniciando sistema LoRa + GPS + SD + OLED...");

  // Inicia GPS
  Serial2.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, -1);
  Serial.println("GPS: aguardando sinal...");

  // Inicia OLED
  Wire.begin(21, 22);  // SDA, SCL
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Falha ao iniciar o display SSD1306"));
    while (true)
      ;
  }
  display.setRotation(2);
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("Iniciando...");
  display.display();

  // Inicia LoRa (VSPI)
  LoRa.setPins(LORA_CS_PIN, LORA_RST_PIN, LORA_IRQ_PIN);
  if (!LoRa.begin(433E6)) {
    Serial.println("Falha ao iniciar LoRa!");
    display.println("LoRa FALHOU!");
    display.display();
    while (true)
      ;
  }
  LoRa.setSpreadingFactor(8);
  Serial.println("LoRa OK");
  display.println("LoRa OK");
  display.display();
  delay(1000);

  // Inicia SD via HSPI
  hspi = new SPIClass(HSPI);
  hspi->begin(14, 12, 13, SD_CS_PIN);  // SCK, MISO, MOSI, CS

  if (!SD.begin(SD_CS_PIN, *hspi)) {
    Serial.println("Falha ao inicializar cartão SD!");
    display.println("SD FALHOU!");
    display.display();
  } else {
    sdInitialized = true;
    Serial.println("Cartão SD OK");
    display.println("SD OK");
    display.display();

    uint8_t cardType = SD.cardType();

    if (cardType == CARD_NONE) {
      Serial.println("No SD card attached");
      return;
    }

    Serial.print("SD Card Type: ");
    if (cardType == CARD_MMC) {
      Serial.println("MMC");
    } else if (cardType == CARD_SD) {
      Serial.println("SDSC");
    } else if (cardType == CARD_SDHC) {
      Serial.println("SDHC");
    } else {
      Serial.println("UNKNOWN");
    }

    uint64_t cardSize = SD.cardSize() / (1024 * 1024);
    Serial.printf("SD Card Size: %lluMB\n", cardSize);
    Serial.println("Inicialização do SD OK!");
    display.println("SD OK");
  }
  delay(1000);
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  // ---------- Leitura do GPS ----------
  while (Serial2.available() > 0) gps.encode(Serial2.read());

  // ---------- Recepção LoRa ----------
  int packetSize = LoRa.parsePacket();
  if (packetSize > 0) {
    lastLoRaMessage = "";
    while (LoRa.available()) {
      lastLoRaMessage += (char)LoRa.read();
    }
    lastLoRaRSSI = LoRa.packetRssi();
    lastLoRaSNR = LoRa.packetSnr();
  }

  // ---------- Escaneamento Wi-Fi Passivo (a cada 5s) ----------
  static unsigned long lastWiFiScan = 0;
  if (millis() - lastWiFiScan > 5000) {  // A cada 5 segundos
    scanWiFiPassive();
    lastWiFiScan = millis();
  }

  // ---------- Atualização de Display e Gravação no SD ----------
  if (millis() - lastDisplayUpdate > displayInterval && gps.location.isUpdated()) {
    lastDisplayUpdate = millis();

    // Mostra no Serial
    Serial.print("Mensagem LoRa: ");
    Serial.println(lastLoRaMessage);
    Serial.print("RSSI LoRa: ");
    Serial.println(lastLoRaRSSI);
    Serial.print("SNR LoRa: ");
    Serial.println(lastLoRaSNR, 1);
   
    Serial.print(wifiData);
    Serial.println();
    Serial.print("Lat: ");
    Serial.println(gps.location.lat(), 7);
    Serial.print("Lng: ");
    Serial.println(gps.location.lng(), 7);
    Serial.print("Sat: ");
    Serial.println(gps.satellites.value());
    Serial.print("HDOP: ");
    Serial.println(gps.hdop.hdop(), 6);
    Serial.println("------------------");

    // Atualiza OLED
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println(lastLoRaMessage);
    display.print("LoRa: ");
    display.print(lastLoRaRSSI);
    display.print("  SNR: ");
    display.println(lastLoRaSNR, 1);
    display.print("Wi-Fi: ");
    display.println(strongestWiFiRSSI);
    display.println();
    display.print("Lat: ");
    display.println(gps.location.lat(), 6);
    display.print("Lng: ");
    display.println(gps.location.lng(), 6);
    display.print("Sat: ");
    display.println(gps.satellites.value());
    display.print("HDOP: ");
    display.println(gps.hdop.hdop(), 1);
    display.display();

    // Salva no SD
    saveDataToSD();
  }
}