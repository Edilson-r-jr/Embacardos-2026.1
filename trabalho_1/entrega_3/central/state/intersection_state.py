import time


class IntersectionState:

    def __init__(self, intersection_id: int):

        self.intersection_id = intersection_id

        self.connected = False

        self.last_heartbeat = None

        self.vehicle_count = {
            1: 0,
            2: 0
        }

        self.average_speed = {
            1: 0.0,
            2: 0.0
        }

        self.speed_violations = 0

    def heartbeat(self):

        self.connected = True

        self.last_heartbeat = time.time()

    def seconds_since_heartbeat(self):

        if self.last_heartbeat is None:
            return None

        return int(
            time.time() - self.last_heartbeat
        )