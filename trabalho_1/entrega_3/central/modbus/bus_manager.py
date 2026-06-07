import threading
from central.modbus.uart_interface import UARTInterface
from central.modbus.crc16 import append_crc, validate_crc


class ModbusBusManager:
    """
    Controla acesso único ao UART (OBRIGATÓRIO para RS485)
    """

    _instance = None
    _lock_instance = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock_instance:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, port="/dev/serial0"):
        if hasattr(self, "initialized"):
            return

        self.uart = UARTInterface(port=port, timeout=0.3)
        self.lock = threading.Lock()
        self.initialized = True

    # =====================================================
    # REQUEST ÚNICO (CORE DO SISTEMA)
    # =====================================================

    def request(self, packet: bytes, response_size: int, strict_crc=True):
        """
        Envia request e lê resposta de forma segura
        """

        with self.lock:

            # limpa lixo antigo
            self.uart.ser.reset_input_buffer()

            packet = append_crc(packet)

            if not self.uart.send_packet(packet):
                return None

            response = self.uart.read_packet(response_size, timeout=0.8)

            if len(response) < response_size:
                return None

            if strict_crc and not validate_crc(response):
                return None

            return response