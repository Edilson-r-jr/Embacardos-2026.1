from central.modbus.bus_manager import ModbusBusManager
from central.constants import MATRICULA
import time


class LPRCamera:

    def __init__(self, address, port="/dev/serial0"):
        self.address = address
        self.matricula = MATRICULA
        self.bus = ModbusBusManager(port)

    # -----------------------------
    # API principal
    # -----------------------------
    def trigger_capture(self):
        if not self._write_register(1, 1):
            return None, None

        time.sleep(0.2)

        timeout = time.time() + 2.0
        status = None

        while time.time() < timeout:
            status = self._read_register(0)

            if status in [2, 3]:
                break

            time.sleep(0.05)

        if status != 2:
            self._write_register(1, 0)
            return None, None

        regs = self._read_multiple_registers(2, 4)
        if not regs:
            self._write_register(1, 0)
            return None, None

        placa = ""
        for r in regs:
            placa += chr((r >> 8) & 0xFF)
            placa += chr(r & 0xFF)

        placa = placa.replace("\x00", "")
        conf = self._read_register(6)

        self._write_register(1, 0)

        return placa, conf

    # -----------------------------
    # MODBUS WRITE (trigger)
    # -----------------------------
    def _write_register(self, offset, value):

        payload = bytes([
            self.address,
            0x10,
            0x00, offset,
            0x00, 0x01,
            0x02,
            (value >> 8) & 0xFF,
            value & 0xFF
        ])

        packet = payload + self.matricula

        resp = self.bus.request(packet, 8)
        return resp is not None

    # -----------------------------
    # MODBUS READ single register
    # -----------------------------
    def _read_register(self, offset):
        regs = self._read_multiple_registers(offset, 1)
        return regs[0] if regs else None

    # -----------------------------
    # MODBUS READ multiple registers
    # -----------------------------
    def _read_multiple_registers(self, offset, count):

        payload = bytes([
            self.address,
            0x03,
            0x00, offset,
            0x00, count
        ])

        packet = payload + self.matricula

        resp = self.bus.request(packet, 5 + count * 2 + 2)

        if not resp:
            return None

        registers = []
        for i in range(count):
            registers.append((resp[3 + i*2] << 8) | resp[4 + i*2])

        return registers