/*
 * Pet Feeder ESP32 Firmware
 * Controla servo motor para dispensar ração via comandos HTTP
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// ===== CONFIGURAÇÕES WIFI =====
const char* ssid = "SUA_REDE_WIFI";
const char* password = "SUA_SENHA_WIFI";

// ===== CONFIGURAÇÕES DO DISPOSITIVO =====
const char* DEVICE_ID = "petfeeder_001";
const int SERVER_PORT = 80;

// ===== PINOS =====
const int SERVO_PINS[] = {18, 21, 22, 23, 25};
const int SERVO_COUNT = sizeof(SERVO_PINS) / sizeof(SERVO_PINS[0]);
const int TRIG_PIN = 5;      // Ultrassom - Trigger
const int ECHO_PIN = 19;     // Ultrassom - Echo
const int LED_STATUS = 2;    // LED onboard

// ===== SERVO =====
Servo servoMotors[SERVO_COUNT];
const int SERVO_POSICAO_FECHADO = 0;
const int SERVO_POSICAO_ABERTO = 90;
const int TEMPO_DISPENSO_PADRAO = 3000; // ms

// ===== VARIÁVEIS GLOBAIS =====
WebServer server(SERVER_PORT);
Preferences preferences;

struct DeviceState {
  bool isOnline = true;
  int foodLevel = 0;          // % (0-100)
  int batteryLevel = 100;     // % (simulado)
  bool isDispensing = false;
  unsigned long lastFeeding = 0;
  int lastFeedChannel = 0;
} deviceState;

// ===== SETUP =====
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n=== Pet Feeder ESP32 Iniciando ===");
  
  // Inicializar pinos
  pinMode(LED_STATUS, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  // Inicializar servos
  for (int i = 0; i < SERVO_COUNT; i++) {
    servoMotors[i].setPeriodHertz(50);
    servoMotors[i].attach(SERVO_PINS[i], 500, 2400);
    servoMotors[i].write(SERVO_POSICAO_FECHADO);
  }
  
  // Carregar estado salvo
  preferences.begin("feeder", false);
  deviceState.lastFeeding = preferences.getULong("lastFeed", 0);
  
  // Conectar WiFi
  conectarWiFi();
  
  // Configurar rotas HTTP
  setupRoutes();
  
  // Iniciar servidor
  server.begin();
  Serial.println("Servidor HTTP iniciado na porta " + String(SERVER_PORT));
  
  // Medir nível inicial de ração
  atualizarNivelRacao();
}

void loop() {
  server.handleClient();
  
  // Piscar LED para indicar online
  static unsigned long lastBlink = 0;
  if (millis() - lastBlink > 1000) {
    digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
    lastBlink = millis();
  }
  
  // Atualizar nível de ração a cada 30 segundos
  static unsigned long lastLevelCheck = 0;
  if (millis() - lastLevelCheck > 30000) {
    atualizarNivelRacao();
    lastLevelCheck = millis();
  }
}

// ===== FUNÇÕES DE CONECTIVIDADE =====
void conectarWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  Serial.print("Conectando ao WiFi");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi conectado!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFalha ao conectar WiFi. Reiniciando...");
    ESP.restart();
  }
}

// ===== ROTAS HTTP =====
void setupRoutes() {
  // Rota raiz - status
  server.on("/", HTTP_GET, handleRoot);
  
  // Rota de status do dispositivo
  server.on("/api/status", HTTP_GET, handleStatus);
  
  // Rota para dispensar ração
  server.on("/api/feed", HTTP_POST, handleFeed);
  
  // Rota para calibrar servo
  server.on("/api/calibrate", HTTP_POST, handleCalibrate);
  
  // CORS preflight
  server.onNotFound(handleNotFound);
}

void handleRoot() {
  StaticJsonDocument<256> doc;
  doc["device_id"] = DEVICE_ID;
  doc["name"] = "Pet Feeder ESP32";
  doc["version"] = "1.0.0";
  doc["status"] = "online";
  doc["ip"] = WiFi.localIP().toString();
  
  sendJsonResponse(doc, 200);
}

void handleStatus() {
  StaticJsonDocument<512> doc;
  doc["device_id"] = DEVICE_ID;
  doc["online"] = deviceState.isOnline;
  doc["food_level"] = deviceState.foodLevel;
  doc["battery_level"] = deviceState.batteryLevel;
  doc["is_dispensing"] = deviceState.isDispensing;
  doc["last_feed_channel"] = deviceState.lastFeedChannel;
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["last_feeding"] = deviceState.lastFeeding;
  doc["timestamp"] = millis();
  
  sendJsonResponse(doc, 200);
}

void handleFeed() {
  if (deviceState.isDispensing) {
    StaticJsonDocument<128> doc;
    doc["success"] = false;
    doc["error"] = "Dispensando em andamento";
    sendJsonResponse(doc, 409);
    return;
  }
  
  // Parse do body JSON
  StaticJsonDocument<256> requestBody;
  if (server.hasArg("plain")) {
    deserializeJson(requestBody, server.arg("plain"));
  }
  
  int quantity = requestBody["quantity"] | 50;  // Default 50g
  int duration = requestBody["duration"] | TEMPO_DISPENSO_PADRAO;
  int channel = requestBody["channel"] | 0;
  String feedingId = requestBody["feeding_id"] | "manual_" + String(millis());
  
  Serial.println("Comando de alimentação recebido:");
  Serial.println("  Quantidade: " + String(quantity) + "g");
  Serial.println("  Duração: " + String(duration) + "ms");
  Serial.println("  Canal: " + String(channel));
  
  // Executar dispensação
  bool success = dispensarRacao(duration, channel);
  
  if (success) {
    deviceState.lastFeeding = millis();
    preferences.putULong("lastFeed", deviceState.lastFeeding);
    atualizarNivelRacao();
  }
  
  // Responder
  StaticJsonDocument<512> doc;
  doc["success"] = success;
  doc["feeding_id"] = feedingId;
  doc["quantity"] = quantity;
  doc["channel"] = channel;
  doc["timestamp"] = millis();
  doc["food_level_after"] = deviceState.foodLevel;
  
  sendJsonResponse(doc, success ? 200 : 500);
}

void handleCalibrate() {
  StaticJsonDocument<256> requestBody;
  if (server.hasArg("plain")) {
    deserializeJson(requestBody, server.arg("plain"));
  }
  
  int pos = requestBody["position"] | 0;
  int channel = requestBody["channel"] | 0;
  
  Serial.println("Calibrando servo no canal " + String(channel) + " para posição: " + String(pos));
  if (channel < 0 || channel >= SERVO_COUNT) {
    StaticJsonDocument<128> doc;
    doc["success"] = false;
    doc["error"] = "Canal inválido";
    sendJsonResponse(doc, 400);
    return;
  }
  servoMotors[channel].write(pos);
  
  StaticJsonDocument<128> doc;
  doc["success"] = true;
  doc["position"] = pos;
  doc["channel"] = channel;
  sendJsonResponse(doc, 200);
}

void handleNotFound() {
  if (server.method() == HTTP_OPTIONS) {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
    server.send(204);
  } else {
    StaticJsonDocument<128> doc;
    doc["error"] = "Not found";
    sendJsonResponse(doc, 404);
  }
}

// ===== FUNÇÕES AUXILIARES =====
bool dispensarRacao(int duracaoMs, int channel) {
  if (channel < 0 || channel >= SERVO_COUNT) {
    Serial.println("ERRO: Canal de servo inválido: " + String(channel));
    return false;
  }
  if (deviceState.foodLevel < 5) {
    Serial.println("ERRO: Nível de ração muito baixo!");
    return false;
  }
  
  deviceState.isDispensing = true;
  deviceState.lastFeedChannel = channel;
  
  // Abrir servo
  Serial.println("Abrindo compartimento do canal " + String(channel) + "...");
  servoMotors[channel].write(SERVO_POSICAO_ABERTO);
  delay(200);  // Tempo para movimento
  
  // Manter aberto pelo tempo especificado
  delay(duracaoMs);
  
  // Fechar servo
  Serial.println("Fechando compartimento do canal " + String(channel) + "...");
  servoMotors[channel].write(SERVO_POSICAO_FECHADO);
  delay(200);
  
  deviceState.isDispensing = false;
  Serial.println("Dispensação concluída!");
  
  return true;
}

void atualizarNivelRacao() {
  // Medir distância com sensor ultrassônico HC-SR04
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);  // Timeout 30ms
  float distance = duration * 0.034 / 2;  // cm
  
  // Converter distância em % de ração (ajuste conforme seu recipiente)
  // Assumindo: 5cm = cheio (100%), 25cm = vazio (0%)
  const float CHEIO_CM = 5.0;
  const float VAZIO_CM = 25.0;
  
  int percentage = map(constrain(distance, CHEIO_CM, VAZIO_CM), VAZIO_CM, CHEIO_CM, 0, 100);
  deviceState.foodLevel = percentage;
  
  Serial.println("Nível de ração: " + String(percentage) + "% (distância: " + String(distance) + "cm)");
}

void sendJsonResponse(JsonDocument& doc, int code) {
  String response;
  serializeJson(doc, response);
  
  server.sendHeader("Content-Type", "application/json");
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(code, "application/json", response);
}
