import serial
import time


class UARTInterface:
    def __init__(self, port="/dev/serial0", baudrate=115200, timeout=0.5):
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )

            if self.ser.is_open:
                print(f"[UART] Conectado em {port} @ {baudrate}")

        except Exception as e:
            print(f"Erro ao abrir porta serial {port}: {e}")
            self.ser = None

    def send_packet(self, packet: bytes) -> bool:
        """
        Envia pacote MODBUS sem limpar buffers (importante para RS485)
        """
        if self.ser is None or not self.ser.is_open:
            return False

        try:
            self.ser.write(packet)
            self.ser.flush()
            return True

        except Exception as e:
            print(f"Erro ao enviar pacote: {e}")
            return False

    def read_packet(self, expected_size: int, timeout: float = 1.0) -> bytes:
        """
        Leitura robusta para MODBUS RTU:
        - aguarda bytes chegarem gradualmente
        - respeita timeout total
        """
        if self.ser is None or not self.ser.is_open:
            return b''

        buffer = b''
        start_time = time.time()

        while len(buffer) < expected_size:
            if time.time() - start_time > timeout:
                break

            try:
                chunk = self.ser.read(expected_size - len(buffer))
                if chunk:
                    buffer += chunk
            except Exception as e:
                print(f"Erro ao ler pacote: {e}")
                break

        return buffer

    def read_available(self) -> bytes:
        """
        Lê tudo que estiver disponível no buffer (debug útil)
        """
        if self.ser is None or not self.ser.is_open:
            return b''

        try:
            return self.ser.read_all()
        except Exception:
            return b''

    def close(self):
        """
        Fecha conexão serial
        """
        if self.ser:
            self.ser.close()
            print("[UART] Conexão fechada")