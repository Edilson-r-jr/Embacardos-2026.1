import threading
import time
from central.modbus.bus_manager import ModbusBusManager


class EmergencyReader:

    def __init__(self, port="/dev/serial0"):
        self.bus = ModbusBusManager(port)
        self.state = None
        self.lock = threading.Lock()
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def get_state(self):
        with self.lock:
            return self.state.copy() if self.state else None

    def _loop(self):
        while self.running:
            try:
                state = self.read()
                if state:
                    with self.lock:
                        self.state = state
            except Exception as e:
                print("[EMERGENCY] error:", e)

            time.sleep(0.3)

    def read(self):
        DEVICE = 0x20
        FUNC = 0x03
        START = 0x0000
        QTD = 0x000B

        packet = bytes([
            DEVICE,
            FUNC,
            (START >> 8) & 0xFF,
            START & 0xFF,
            (QTD >> 8) & 0xFF,
            QTD & 0xFF
        ])

        # 3 + (11*2) + 2 = 27 bytes
        response = self.bus.request(packet, 27)

        if not response:
            return None

        return {
            'active': response[3],
            'road': response[5],
            'direction': response[7],
            'intersection_id': response[9],
            'vehicle_type': response[11],
            'signal_group': response[13],
            'timed_out': response[15],
            'unattended_count': response[17],
            'elapsed_s_x10': response[19],
            'max_time_s_x10': response[21],
            'night_mode': response[23],
        }