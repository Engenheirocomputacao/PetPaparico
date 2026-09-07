# ESP32 Pet Feeder Integration

Integração do alimentador de pets com ESP32 para controle de servo motor via WiFi.

## 📁 Estrutura

```
esp32_firmware/
├── pet_feeder_esp32.ino    # Firmware Arduino para ESP32
├── README.md               # Este arquivo
└── diagram.json            # Diagrama de conexões (opcional)
```

## 🔌 Hardware Necessário

| Componente | Pino ESP32 | Função |
|------------|-----------|--------|
| Servo SG90/MG996R | GPIO 18 | Abertura do compartimento |
| HC-SR04 Trigger | GPIO 5 | Medir nível de ração |
| HC-SR04 Echo | GPIO 19 | Medir nível de ração |
| LED Onboard | GPIO 2 | Indicador de status |

## ⚙️ Configuração do Firmware

### 1. Instalar Dependências Arduino IDE

Na Arduino IDE, instalar:
- **ESP32Servo** by Kevin Harrington
- **ArduinoJson** by Benoit Blanchon
- **Preferences** (incluso no ESP32 core)

### 2. Configurar WiFi

Editar no arquivo `.ino`:
```cpp
const char* ssid = "SUA_REDE_WIFI";
const char* password = "SUA_SENHA_WIFI";
```

### 3. Upload para ESP32

1. Conectar ESP32 via USB
2. Selecionar board: `Tools > Board > ESP32 Arduino > ESP32 Dev Module`
3. Porta COM correta
4. Click em **Upload**

## 🌐 Endpoints HTTP do ESP32

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Informações do dispositivo |
| GET | `/api/status` | Status completo (nível de ração, bateria, etc) |
| POST | `/api/feed` | Acionar alimentação |
| POST | `/api/calibrate` | Calibrar posição do servo |

### Exemplo POST /api/feed

```json
{
  "quantity": 50,
  "duration": 3000,
  "feeding_id": "manual_123"
}
```

**Resposta:**
```json
{
  "success": true,
  "feeding_id": "manual_123",
  "quantity": 50,
  "timestamp": 1234567890,
  "food_level_after": 85
}
```

## 🔧 Backend Django

### Configurar IP do ESP32

Em `server_django/pet_feeder_django/settings.py`:

```python
ESP32_BASE_URL = 'http://192.168.1.100'  # IP do seu ESP32
```

Ou definir via variável de ambiente.

### Novas Rotas API

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/feed/` | Acionar alimentação via ESP32 |
| GET | `/api/device/status/` | Status do ESP32 |
| POST | `/api/device/test/` | Testar conexão |
| POST | `/api/servo/calibrate/` | Calibrar servo |

### Testar Conexão

```bash
# Testar se Django consegue comunicar com ESP32
curl -X POST http://localhost:8000/api/device/test/
```

## 📡 Fluxo de Comunicação

```
┌─────────────┐     POST /api/feed/     ┌──────────────┐     POST /api/feed      ┌─────────┐
│   React UI  │ ──────────────────────> │ Django API   │ ─────────────────────> │  ESP32  │
│             │                         │              │                        │ + Servo │
│             │ <────────────────────── │              │ <───────────────────── │         │
└─────────────┘    {success, history}     └──────────────┘   {success, food_lvl}  └─────────┘
```

## 🎯 Próximos Passos Sugeridos

1. **Integrar com Frontend**: Criar botão "Alimentar Agora" que chama `/api/feed/`
2. **Agendamento Automático**: Celery/Django Q para acionar ESP32 nos horários agendados
3. **Notificações**: WebSocket ou push quando alimentação for concluída
4. **MQTT**: Substituir HTTP por MQTT para comunicação mais eficiente
5. **OTA Updates**: Atualização de firmware via rede

## ⚡ Esquema de Conexões

```
ESP32
 ├── GPIO 18 ───────> Servo Signal (PWM)
 ├── GPIO 5  ───────> HC-SR04 Trigger
 ├── GPIO 19 ───────> HC-SR04 Echo
 ├── 3.3V/5V ───────> VCC (Servo, Sensor)
 ├── GND ───────────> GND (Servo, Sensor)
 └── USB/5V ───────> Alimentação externa (recomendado para servo)
```

> ⚠️ **Atenção**: Servos consomem muita corrente. Use fonte externa 5V 2A para o servo.

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| ESP32 não conecta WiFi | Verificar SSID/senha; checar distância do roteador |
| Servo não gira | Verificar alimentação; testar com código simples |
| Nível de ração errado | Calibrar distâncias CHEIO/VAZIO no código |
| Timeout no Django | Verificar firewall; testar `ping` para IP do ESP32 |
| CORS error | Verificar `CORS_ALLOW_ALL_ORIGINS = True` em dev |
