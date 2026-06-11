import time
from collections import deque


class IntersectionState:

    HEARTBEAT_TIMEOUT = 5
    RATE_WINDOW_SEC   = 30  # janela deslizante para cálculo de taxa

    def __init__(self, intersection_id):

        self.intersection_id = intersection_id

        self.last_heartbeat = None

        self.vehicle_count   = {}
        self.vehicle_rate    = {}   # carros/min por sensor
        self._count_history  = {}   # sid -> deque de (timestamp, contagem_cumulativa)

        self.speed_violations = 0

        self.last_speed = {}
        self.avg_speed  = {}   # velocidade média das infrações por sensor

    def heartbeat(self):

        self.last_heartbeat = time.time()

    def is_online(self):

        if self.last_heartbeat is None:
            return False

        return (time.time() - self.last_heartbeat) < self.HEARTBEAT_TIMEOUT

    def update_vehicle_count(self, sensor_id, count):
        sid = int(sensor_id)
        now = time.time()

        self.vehicle_count[sid] = count

        if sid not in self._count_history:
            self._count_history[sid] = deque()

        history = self._count_history[sid]
        history.append((now, count))

        # Remove entradas fora da janela, mantendo ao menos uma
        cutoff = now - self.RATE_WINDOW_SEC
        while len(history) > 1 and history[0][0] < cutoff:
            history.popleft()

        # Taxa = delta de contagem / duração da janela
        if len(history) >= 2:
            t0, c0 = history[0]
            t1, c1 = history[-1]
            elapsed_min = (t1 - t0) / 60.0
            if elapsed_min > 0 and c1 >= c0:
                self.vehicle_rate[sid] = (c1 - c0) / elapsed_min

    def register_violation(self, sensor_id, speed):
        sensor_id = int(sensor_id)

        self.speed_violations += 1
        self.last_speed[sensor_id] = speed

        prev = self.avg_speed.get(sensor_id, 0.0)
        n = self.speed_violations
        self.avg_speed[sensor_id] = prev + (speed - prev) / n

    def seconds_since_heartbeat(self):

        if self.last_heartbeat is None:
            return None

        return int(time.time() - self.last_heartbeat)
