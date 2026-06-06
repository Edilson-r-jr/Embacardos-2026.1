import time


class IntersectionState:

    HEARTBEAT_TIMEOUT = 5

    def __init__(self, intersection_id):

        self.intersection_id = intersection_id

        self.last_heartbeat = None

        self.vehicle_count = {}

        self.speed_violations = 0

        self.last_speed = {}

    def heartbeat(self):

        self.last_heartbeat = time.time()

    def is_online(self):

        if self.last_heartbeat is None:
            return False

        return (
            time.time() -
            self.last_heartbeat
        ) < self.HEARTBEAT_TIMEOUT

    def update_vehicle_count(
        self,
        sensor_id,
        count
    ):

        self.vehicle_count[sensor_id] = count

    def register_violation(
        self,
        sensor_id,
        speed
    ):

        self.speed_violations += 1
        self.last_speed[sensor_id] = speed

    def seconds_since_heartbeat(self):

        if self.last_heartbeat is None:
            return None

        return int(
            time.time() -
            self.last_heartbeat
        )