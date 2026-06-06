"""
Controlador de semáforos via GPIO
"""

from distributed.gpio.gpio_interface import get_gpio_interface
from distributed.constants import GPIO_TRAFFIC_CONTROL


class TrafficLightController:
    """Controla os semáforos via GPIO (3 bits por cruzamento)"""
    
    def __init__(self, intersection_id, use_mock=False):
        self.intersection_id = intersection_id
        self.gpio = get_gpio_interface(use_mock=use_mock)
        self.pins = self._get_pins_for_intersection(intersection_id)
        self._setup_pins()
    
    def _get_pins_for_intersection(self, intersection_id):
        """Retorna os 3 pinos de controle do cruzamento"""
        pins = {}
        for (inter_id, bit), gpio_pin in GPIO_TRAFFIC_CONTROL.items():
            if inter_id == intersection_id:
                pins[bit] = gpio_pin
        return pins
    
    def _setup_pins(self):
        """Configura os pinos como saídas"""
        for bit, pin in self.pins.items():
            self.gpio.setup_output(pin)
            print(f"[TRAFFIC] Cruzamento {self.intersection_id}, Bit {bit} -> GPIO {pin}")
    
    def set_state(self, state_code):
        """
        Define estado do semáforo via código de 3 bits
        
        state_code: 0-7
        Bit 0, 1, 2 correspondem aos 3 pinos
        """
        if state_code < 0 or state_code > 7:
            print(f"[TRAFFIC] Código inválido: {state_code}")
            return
        
        # Extrai cada bit
        bit0 = (state_code >> 0) & 1
        bit1 = (state_code >> 1) & 1
        bit2 = (state_code >> 2) & 1
        
        # Escreve em cada pino
        if 0 in self.pins:
            self.gpio.set_output(self.pins[0], bit0)
        if 1 in self.pins:
            self.gpio.set_output(self.pins[1], bit1)
        if 2 in self.pins:
            self.gpio.set_output(self.pins[2], bit2)
    
    def cleanup(self):
        """Limpa GPIO"""
        self.gpio.cleanup()
