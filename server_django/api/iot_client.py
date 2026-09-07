"""
Cliente IoT para comunicação com ESP32 via HTTP
"""
import time
import requests
from typing import Optional, Dict, Any
from django.conf import settings


class ESP32Client:
    """Cliente HTTP para comunicação com o ESP32 Pet Feeder"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or getattr(settings, 'ESP32_BASE_URL', 'http://192.168.1.100')
        self.timeout = 10  # segundos
        
        # Estado simulado em memória por canal (0-4)
        self.simulator_enabled = True
        self.simulated_states = {
            0: {
                "online": True,
                "food_level": 85,
                "battery_level": 92,
                "is_dispensing": False,
                "wifi_rssi": -45,
                "last_feeding": None,
                "ip": "192.168.1.150 (Simulado)",
                "device_id": "petfeeder_simulated_0",
                "dispensing_until": 0.0,
                "last_dispense_quantity": 50
            },
            1: {
                "online": True,
                "food_level": 60,
                "battery_level": 88,
                "is_dispensing": False,
                "wifi_rssi": -50,
                "last_feeding": None,
                "ip": "192.168.1.150 (Simulado)",
                "device_id": "petfeeder_simulated_1",
                "dispensing_until": 0.0,
                "last_dispense_quantity": 50
            },
            2: {
                "online": True,
                "food_level": 100,
                "battery_level": 95,
                "is_dispensing": False,
                "wifi_rssi": -40,
                "last_feeding": None,
                "ip": "192.168.1.150 (Simulado)",
                "device_id": "petfeeder_simulated_2",
                "dispensing_until": 0.0,
                "last_dispense_quantity": 50
            },
            3: {
                "online": True,
                "food_level": 30,
                "battery_level": 82,
                "is_dispensing": False,
                "wifi_rssi": -55,
                "last_feeding": None,
                "ip": "192.168.1.150 (Simulado)",
                "device_id": "petfeeder_simulated_3",
                "dispensing_until": 0.0,
                "last_dispense_quantity": 50
            },
            4: {
                "online": True,
                "food_level": 75,
                "battery_level": 90,
                "is_dispensing": False,
                "wifi_rssi": -48,
                "last_feeding": None,
                "ip": "192.168.1.150 (Simulado)",
                "device_id": "petfeeder_simulated_4",
                "dispensing_until": 0.0,
                "last_dispense_quantity": 50
            }
        }
    
    @property
    def simulated_state(self) -> Dict[str, Any]:
        """Compatibilidade: estado simulado único para canal 0."""
        return self.simulated_states.get(0, {})
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Faz requisição HTTP para o ESP32"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=self.timeout)
            else:
                return None
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            return {"error": "Timeout - ESP32 não respondeu", "online": False}
        except requests.exceptions.ConnectionError:
            return {"error": "Conexão falhou - ESP32 offline", "online": False}
        except Exception as e:
            return {"error": str(e), "online": False}
    
    def get_status(self, channel: int = None) -> Optional[Dict]:
        """Obtém status do dispositivo ESP32 (ou simulador se ativado)"""
        if self.simulator_enabled:
            current_time = time.time()
            
            # Se canal não especificado, retorna status do canal 0 (compatibilidade)
            if channel is None:
                channel = 0
            
            state = self.simulated_states.get(channel)
            if not state:
                return None
            
            # Atualizar estado de dispensação baseado no tempo decorrido
            if state["dispensing_until"] > 0:
                if current_time < state["dispensing_until"]:
                    state["is_dispensing"] = True
                else:
                    if state["is_dispensing"]:
                        # Concluiu dispensação - atualiza nível de ração e registra
                        state["is_dispensing"] = False
                        quantity = state.get("last_dispense_quantity", 50)
                        reduction = max(1, int(quantity / 5))  # ex: 50g -> 10%
                        state["food_level"] = max(0, state["food_level"] - reduction)
                        state["last_feeding"] = int(current_time * 1000)
                        state["dispensing_until"] = 0.0
            
            if not state["online"]:
                return None  # Indica offline
                
            return {
                "device_id": state["device_id"],
                "channel": channel,
                "online": True,
                "food_level": state["food_level"],
                "battery_level": state["battery_level"],
                "is_dispensing": state["is_dispensing"],
                "wifi_rssi": state["wifi_rssi"],
                "last_feeding": state["last_feeding"],
                "timestamp": int(current_time * 1000),
                "ip": state["ip"]
            }
            
        # Para hardware real, adicionar parâmetro channel na requisição
        endpoint = "/api/status"
        if channel is not None:
            endpoint = f"/api/status?channel={channel}"
        return self._request("GET", endpoint)
    
    def get_all_channels_status(self) -> Dict[int, Optional[Dict]]:
        """Obtém status de todos os canais (0-4)"""
        status_by_channel = {}
        for channel in range(5):
            status_by_channel[channel] = self.get_status(channel)
        return status_by_channel
    
    def dispense_food(self, quantity: int = 50, duration_ms: int = 3000, 
                      feeding_id: str = None, channel: int = None) -> Dict[str, Any]:
        """
        Envia comando para dispensar ração (ou simula se ativado)
        """
        if self.simulator_enabled:
            if channel is None:
                return {"error": "Canal não especificado", "success": False}
            
            state = self.simulated_states.get(channel)
            if not state or not state["online"]:
                return {"error": f"Dispensador {channel} offline", "success": False}
            
            if state["food_level"] < 5:
                return {"error": f"Nível de ração muito baixo no dispensador {channel}!", "success": False}
                
            current_time = time.time()
            state["is_dispensing"] = True
            state["dispensing_until"] = current_time + (duration_ms / 1000.0)
            state["last_dispense_quantity"] = quantity
            
            reduction = max(1, int(quantity / 5))
            food_level_after = max(0, state["food_level"] - reduction)
            state["food_level"] = food_level_after
            
            return {
                "success": True,
                "feeding_id": feeding_id or f"feed_{int(current_time)}",
                "quantity": quantity,
                "channel": channel,
                "timestamp": int(current_time * 1000),
                "food_level_after": food_level_after
            }
            
        data = {
            "quantity": quantity,
            "duration": duration_ms,
            "feeding_id": feeding_id or f"feed_{int(time.time())}"
        }
        if channel is not None:
            data["channel"] = channel
        return self._request("POST", "/api/feed", data)
    
    def calibrate_servo(self, position: int = 0, channel: int = None) -> Optional[Dict]:
        """Calibra o servo para uma posição específica (0-90) em um canal específico"""
        position = max(0, min(90, position))
        if self.simulator_enabled:
            if channel is None:
                return {"error": "Canal não especificado", "success": False}
            
            state = self.simulated_states.get(channel)
            if not state or not state["online"]:
                return {"error": f"Dispensador {channel} offline", "success": False}
            
            return {
                "success": True,
                "position": position,
                "channel": channel
            }
            
        data = {"position": position}
        if channel is not None:
            data["channel"] = channel
        return self._request("POST", "/api/calibrate", data)
    
    def is_online(self, channel: int = None) -> bool:
        """Verifica se o ESP32/canal específico está online"""
        if self.simulator_enabled:
            if channel is None:
                # Verifica se pelo menos um canal está online
                return any(state["online"] for state in self.simulated_states.values())
            state = self.simulated_states.get(channel)
            return state is not None and state["online"]
        
        status = self.get_status(channel)
        return status is not None and status.get("online", False)
    
    def get_channel_status(self, channel: int) -> Optional[Dict]:
        """Obtém status de um canal específico (alias para get_status com channel)"""
        return self.get_status(channel)
        
    def update_simulator(self, data: Dict[str, Any], channel: int = None) -> Dict[str, Any]:
        """Atualiza as configurações do simulador para um canal específico ou todos"""
        if channel is not None:
            # Atualizar canal específico
            state = self.simulated_states.get(channel)
            if state:
                if "online" in data:
                    state["online"] = bool(data["online"])
                if "food_level" in data:
                    state["food_level"] = max(0, min(100, int(data["food_level"])))
                if "battery_level" in data:
                    state["battery_level"] = max(0, min(100, int(data["battery_level"])))
                if "wifi_rssi" in data:
                    state["wifi_rssi"] = int(data["wifi_rssi"])
        else:
            # Atualizar todos os canais
            for ch in range(5):
                state = self.simulated_states.get(ch)
                if state:
                    if "online" in data:
                        state["online"] = bool(data["online"])
                    if "food_level" in data:
                        state["food_level"] = max(0, min(100, int(data["food_level"])))
                    if "battery_level" in data:
                        state["battery_level"] = max(0, min(100, int(data["battery_level"])))
                    if "wifi_rssi" in data:
                        state["wifi_rssi"] = int(data["wifi_rssi"])
        
        if "simulator_enabled" in data:
            self.simulator_enabled = bool(data["simulator_enabled"])
            
        return {
            "simulator_enabled": self.simulator_enabled,
            "states": self.simulated_states
        }


# Instância singleton do cliente
esp32_client = ESP32Client()
