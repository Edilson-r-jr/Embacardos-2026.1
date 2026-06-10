import threading
import time
from central.modbus.bus_manager import ModbusBusManager
from central.constants import MATRICULA


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
                    #print("[RAW STATE]", state)
                    
                    with self.lock:
                        self.state = state
            except Exception as e:
                print("[EMERGENCY] error:", e)

            time.sleep(0.3)

    def read(self):
        DEVICE = 0x20
        FUNC = 0x03
        START = 0x0000
        QTD = 0x0000

        packet = bytes([
            0x20,        # addr
            0x03,        # func
            0x00, 0x00,  # start
            0x0B, 0x00   # qty
        ]) + MATRICULA

        # 3 + (11*2) + 2 = 27 bytes
        response = self.bus.request(packet, 27)

        #print("RAW RESPONSE:", [f"{b:02X}" for b in response])

        if not response:
            return None

        regs = []

        for i in range(11):
            pos = 3 + i * 2
            regs.append((response[pos] << 8) | response[pos + 1])

        

        return {
            'active': regs[0],
            'road': regs[1],
            'direction': regs[2],
            'intersection_id': regs[3],
            'vehicle_type': regs[4],
            'signal_group': regs[5],
            'timed_out': regs[6],
            'unattended_count': regs[7],
            'elapsed_s_x10': regs[8],
            'max_time_s_x10': regs[9],
            'night_mode': regs[10],
        }