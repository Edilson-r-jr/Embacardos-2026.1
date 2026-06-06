import json
import os
import threading

from central.state.intersection_state import (
    IntersectionState
)


class StateManager:

    STATE_FILE = "system_state.json"

    def __init__(self, violation_callback=None):

        self.lock = threading.Lock()

        self.intersections = {
            1: IntersectionState(1),
            2: IntersectionState(2)
        }
        
        self.violation_callback = violation_callback
        self.night_mode = False
        self.emergency_active = False
        self.emergency_state = None

        self.load_state()

    def load_state(self):
        """Carrega estado persistente do disco"""
        if not os.path.exists(self.STATE_FILE):
            return

        try:
            with open(self.STATE_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            with self.lock:
                self.night_mode = data.get("night_mode", False)
                self.emergency_active = data.get("emergency_active", False)
                self.emergency_state = data.get("emergency_state")

                intersections = data.get("intersections", {})
                for intersection_id, intersection_data in intersections.items():
                    intersection_id = int(intersection_id)
                    if intersection_id in self.intersections:
                        intersection = self.intersections[intersection_id]
                        intersection.vehicle_count = intersection_data.get("vehicle_count", intersection.vehicle_count)
                        intersection.speed_violations = intersection_data.get("speed_violations", intersection.speed_violations)
                        intersection.last_speed = intersection_data.get("last_speed", intersection.last_speed)
        except Exception as error:
            print(f"[STATE] Falha ao carregar estado persistente: {error}")

    def save_state(self):
        """Salva estado persistente no disco"""
        data = {
            "night_mode": self.night_mode,
            "emergency_active": self.emergency_active,
            "emergency_state": self.emergency_state,
            "intersections": {
                intersection_id: {
                    "vehicle_count": intersection.vehicle_count,
                    "speed_violations": intersection.speed_violations,
                    "last_speed": intersection.last_speed
                }
                for intersection_id, intersection in self.intersections.items()
            }
        }

        try:
            with open(self.STATE_FILE, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
        except Exception as error:
            print(f"[STATE] Falha ao salvar estado persistente: {error}")

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
                
                # Chama callback para processar violação
                if self.violation_callback:
                    self.violation_callback(
                        intersection_id,
                        message["sensor_id"],
                        message["speed"]
                    )

            self.save_state()

    def get_snapshot(self):

        with self.lock:

            return self.intersections
    
    def set_night_mode(self, enabled):
        """Ativa/desativa modo noturno"""
        with self.lock:
            self.night_mode = enabled
            self.save_state()
    
    def is_night_mode(self):
        """Verifica se modo noturno está ativo"""
        with self.lock:
            return self.night_mode
    
    def set_emergency_active(self, active):
        """Define se há emergência em curso"""
        with self.lock:
            self.emergency_active = active
            self.save_state()
    
    def is_emergency_active(self):
        """Verifica se há emergência em curso"""
        with self.lock:
            return self.emergency_active

    def set_emergency_state(self, state):
        """Armazena o último estado de emergência"""
        with self.lock:
            self.emergency_state = state
            self.save_state()

    def get_emergency_state(self):
        """Retorna o último estado de emergência"""
        with self.lock:
            return self.emergency_state