import threading

from central.state.intersection_state import (
    IntersectionState
)


class StateManager:

    def __init__(self):

        self.lock = threading.Lock()

        self.intersections = {
            1: IntersectionState(1),
            2: IntersectionState(2)
        }

    def process_message(
        self,
        message
    ):

        msg_type = message.get("type")

        intersection_id = message.get(
            "intersection_id"
        )

        if intersection_id not in self.intersections:
            return

        intersection = (
            self.intersections[
                intersection_id
            ]
        )

        with self.lock:

            if msg_type == "heartbeat":

                intersection.heartbeat()

            elif msg_type == "vehicle_count":

                intersection.update_vehicle_count(
                    message["sensor_id"],
                    message["count"]
                )

            elif msg_type == "speed_violation":

                intersection.register_violation(
                    message["sensor_id"],
                    message["speed"]
                )

    def get_snapshot(self):

        with self.lock:

            return self.intersections