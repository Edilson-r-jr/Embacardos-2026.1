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

    def process_message(self, message):

        msg_type = message.get("type")

        if msg_type == "heartbeat":

            intersection_id = message[
                "intersection_id"
            ]

            with self.lock:

                self.intersections[
                    intersection_id
                ].heartbeat()

    def get_snapshot(self):

        with self.lock:

            return self.intersections