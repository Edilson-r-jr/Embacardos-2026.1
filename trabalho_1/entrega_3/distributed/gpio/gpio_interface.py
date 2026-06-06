"""
Módulo GPIO abstrato - suporta Raspberry Pi real ou mock para testes
"""

import sys


class GPIOInterface:
    """Interface genérica para GPIO - implementada com RPi.GPIO ou mock"""
    
    def setup_output(self, pin):
        """Configura pino como saída"""
        raise NotImplementedError
    
    def setup_input(self, pin, pull_up_down=None):
        """Configura pino como entrada"""
        raise NotImplementedError
    
    def set_output(self, pin, state):
        """Escreve valor em pino de saída (0 ou 1)"""
        raise NotImplementedError
    
    def read_input(self, pin):
        """Lê valor de pino de entrada"""
        raise NotImplementedError
    
    def cleanup(self):
        """Limpa configuração de GPIO"""
        raise NotImplementedError


class MockGPIO(GPIOInterface):
    """Mock de GPIO para testes em ambiente sem Raspberry Pi"""
    
    def __init__(self):
        self.pins = {}
        self.callbacks = {}
    
    def setup_output(self, pin):
        """Configura pino como saída"""
        self.pins[pin] = 0
        print(f"[GPIO Mock] Pino {pin} configurado como saída")
    
    def setup_input(self, pin, pull_up_down=None):
        """Configura pino como entrada"""
        self.pins[pin] = 0
        print(f"[GPIO Mock] Pino {pin} configurado como entrada")
    
    def set_output(self, pin, state):
        """Escreve valor em pino de saída"""
        self.pins[pin] = state
        print(f"[GPIO Mock] Pino {pin} = {state}")
    
    def read_input(self, pin):
        """Lê valor de pino de entrada (retorna valor mockeado)"""
        # Mock: retorna um valor que foi setado
        return self.pins.get(pin, 0)
    
    def cleanup(self):
        """Limpa configuração"""
        self.pins.clear()


class RealGPIO(GPIOInterface):
    """Implementação real com RPi.GPIO para Raspberry Pi"""
    
    def __init__(self):
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(self.GPIO.BCM)
            print("[GPIO] RPi.GPIO inicializado")
        except ImportError:
            raise ImportError("RPi.GPIO não está instalado. Instale com: pip install RPi.GPIO")
        except RuntimeError as e:
            print(f"[GPIO] Erro: {e}")
            print("[GPIO] Execute com sudo ou adicione o usuário ao grupo gpio")
            raise
    
    def setup_output(self, pin):
        """Configura pino como saída"""
        try:
            self.GPIO.setup(pin, self.GPIO.OUT, initial=self.GPIO.LOW)
        except Exception as e:
            print(f"[GPIO] Erro ao configurar pino {pin} como saída: {e}")
    
    def setup_input(self, pin, pull_up_down=None):
        """Configura pino como entrada"""
        try:
            if pull_up_down is not None:
                self.GPIO.setup(pin, self.GPIO.IN, pull_up_down=pull_up_down)
            else:
                self.GPIO.setup(pin, self.GPIO.IN)
        except Exception as e:
            print(f"[GPIO] Erro ao configurar pino {pin} como entrada: {e}")
    
    def set_output(self, pin, state):
        """Escreve valor em pino de saída"""
        try:
            self.GPIO.output(pin, self.GPIO.HIGH if state else self.GPIO.LOW)
        except Exception as e:
            print(f"[GPIO] Erro ao escrever no pino {pin}: {e}")
    
    def read_input(self, pin):
        """Lê valor de pino de entrada"""
        try:
            return self.GPIO.input(pin)
        except Exception as e:
            print(f"[GPIO] Erro ao ler pino {pin}: {e}")
            return 0
    
    def cleanup(self):
        """Limpa configuração de GPIO"""
        try:
            self.GPIO.cleanup()
            print("[GPIO] Limpeza concluída")
        except Exception as e:
            print(f"[GPIO] Erro na limpeza: {e}")


def get_gpio_interface(use_mock=False):
    """
    Factory para obter interface GPIO apropriada
    
    Args:
        use_mock: Se True, força uso de mock. Se False, tenta usar RPi.GPIO.
                 Se não conseguir, usa mock automaticamente.
    """
    if use_mock:
        print("[GPIO] Usando mock (modo testes)")
        return MockGPIO()
    
    try:
        print("[GPIO] Tentando usar RPi.GPIO...")
        return RealGPIO()
    except Exception as e:
        print(f"[GPIO] Não conseguiu usar RPi.GPIO: {e}")
        print("[GPIO] Caindo para mock")
        return MockGPIO()
