import threading
import time

from .traffic_controller import TrafficController
from .traffic_states import TrafficState


class TrafficStateMachine(threading.Thread):

    def __init__(self, intersection_id):
        super().__init__(daemon=True)

        self.intersection_id = intersection_id
        self.current_state = TrafficState.MAIN_GREEN

    def run(self):

        while True:

            duration = TrafficController.get_duration(
                self.current_state
            )

            print(
                f"[DIST {self.intersection_id}] "
                f"{self.current_state.name} "
                f"({duration}s)"
            )

            time.sleep(duration)

            self.current_state = (
                TrafficController.next_state(
                    self.current_state
                )
            )