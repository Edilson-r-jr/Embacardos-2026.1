"""
Leitor de sensores de velocidade e botões de pedestre via GPIO
"""

import threading
import time
from distributed.gpio.gpio_interface import get_gpio_interface
from distributed.constants import GPIO_SPEED_SENSORS, GPIO_PEDESTRIAN_BUTTONS, SENSOR_DISTANCE


class SpeedSensorReader:
    """Lê sensores de velocidade via GPIO"""
    
    def __init__(self, sensor_id, use_mock=False):
        self.sensor_id = sensor_id
        self.gpio = get_gpio_interface(use_mock=use_mock)
        
        if sensor_id not in GPIO_SPEED_SENSORS:
            raise ValueError(f"Sensor {sensor_id} não definido")
        
        self.pin_a = GPIO_SPEED_SENSORS[sensor_id]["a"]
        self.pin_b = GPIO_SPEED_SENSORS[sensor_id]["b"]
        
        self.gpio.setup_input(self.pin_a)
        self.gpio.setup_input(self.pin_b)
        
        self.last_a_state = 0
        self.last_b_state = 0
        self.last_pulse_time = None
        self.speed_kmh = 0
        self.speed_ready = False
        self.vehicle_count = 0
        
        print(f"[SENSOR] Sensor {sensor_id} - Pino A: {self.pin_a}, Pino B: {self.pin_b}")
    
    def read_speed(self):
        """
        Lê a velocidade do sensor
        Retorna velocidade em km/h
        """
        a_state = self.gpio.read_input(self.pin_a)
        b_state = self.gpio.read_input(self.pin_b)
        
        # Detecta borda de subida no pino A
        if a_state == 1 and self.last_a_state == 0:
            self.last_pulse_time = time.time()
        
        # Detecta borda de subida no pino B
        if b_state == 1 and self.last_b_state == 0:
            if self.last_pulse_time is not None:
                delta_t = time.time() - self.last_pulse_time
                
                # Calcula velocidade: v = d / t * 3.6
                # d = 2.5m (distância entre sensores), 3.6 para converter m/s para km/h
                if delta_t > 0:
                    self.speed_kmh = (SENSOR_DISTANCE / delta_t) * 3.6
                    self.speed_ready = True
                    self.vehicle_count += 1
                
                self.last_pulse_time = None
        
        self.last_a_state = a_state
        self.last_b_state = b_state
        
        return self.speed_kmh
    
    def get_vehicle_count(self):
        """Retorna contagem de veículos"""
        return self.vehicle_count

    def pop_vehicle_count(self):
        """Retorna a contagem acumulada desde a última leitura e zera o contador"""
        count = self.vehicle_count
        self.vehicle_count = 0
        return count

    def pop_last_speed(self):
        """Retorna a última velocidade medida e marca o evento como consumido"""
        if not self.speed_ready:
            return None
        speed = self.speed_kmh
        self.speed_ready = False
        self.speed_kmh = 0
        return speed


class PedestrianButtonReader:
    """Lê botões de pedestre via GPIO"""
    
    def __init__(self, intersection_id, use_mock=False):
        self.intersection_id = intersection_id
        self.gpio = get_gpio_interface(use_mock=use_mock)
        self.callbacks = {}
        self.running = False
        self.thread = None
        
        # Configura os botões para este cruzamento
        self.buttons = {}
        
        # Mapeia botões para este cruzamento
        suffix_main = f"{intersection_id}_main"
        suffix_cross = f"{intersection_id}_cross"
        
        if suffix_main in GPIO_PEDESTRIAN_BUTTONS:
            pin = GPIO_PEDESTRIAN_BUTTONS[suffix_main]
            self.buttons["main"] = pin
            self.gpio.setup_input(pin)
            print(f"[PED] Cruzamento {intersection_id} - Botão Principal: GPIO {pin}")
        
        if suffix_cross in GPIO_PEDESTRIAN_BUTTONS:
            pin = GPIO_PEDESTRIAN_BUTTONS[suffix_cross]
            self.buttons["cross"] = pin
            self.gpio.setup_input(pin)
            print(f"[PED] Cruzamento {intersection_id} - Botão Travessia: GPIO {pin}")
        
        self.button_states = {name: 0 for name in self.buttons}
    
    def add_callback(self, button_name, callback):
        """Registra callback para um botão"""
        self.callbacks[button_name] = callback
    
    def start_polling(self):
        """Inicia thread de polling dos botões"""
        self.running = True
        self.thread = threading.Thread(target=self._polling_thread, daemon=True)
        self.thread.start()
    
    def _polling_thread(self):
        """Thread de polling dos botões com debounce"""
        debounce_time = 0.05  # 50ms
        last_press = {}
        
        while self.running:
            current_time = time.time()
            
            for button_name, pin in self.buttons.items():
                state = self.gpio.read_input(pin)
                last_state = self.button_states[button_name]
                
                # Detecta transição de baixo para alto (pressionado)
                if state == 1 and last_state == 0:
                    # Debounce
                    if button_name not in last_press or (current_time - last_press[button_name]) > debounce_time:
                        print(f"[PED] Botão '{button_name}' pressionado")
                        last_press[button_name] = current_time
                        
                        # Chama callback se registrado
                        if button_name in self.callbacks:
                            self.callbacks[button_name]()
                
                self.button_states[button_name] = state
            
            time.sleep(0.01)  # 10ms de intervalo de polling
    
    def stop_polling(self):
        """Para o polling"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
