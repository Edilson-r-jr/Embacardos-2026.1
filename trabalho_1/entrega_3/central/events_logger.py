import json
import os
import threading
from datetime import datetime


class EventsLogger:

    LOG_FILE = "logs/central_events.json"

    def __init__(self):
        self.lock = threading.Lock()
        self.lpr_events  = []
        self.push_events = []
        self.mode_events = []
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.LOG_FILE):
                with open(self.LOG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.lpr_events  = data.get("lpr_events",  [])
                self.push_events = data.get("push_events", [])
                self.mode_events = data.get("mode_events", [])
        except Exception:
            pass

    def _save(self):
        try:
            os.makedirs("logs", exist_ok=True)
            with open(self.LOG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "lpr_events":  self.lpr_events,
                    "push_events": self.push_events,
                    "mode_events": self.mode_events,
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"[CENTRAL] Erro ao salvar events log: {e}")

    def add_lpr_event(self, intersection_id, sensor_id, plate, confidence):
        event = {
            "timestamp":       datetime.now().isoformat(),
            "intersection_id": intersection_id,
            "sensor_id":       sensor_id,
            "plate":           plate,
            "confidence":      confidence,
        }
        with self.lock:
            self.lpr_events.append(event)
            self._save()

    def add_push_event(self, intersection_id, sensor_id, speed_kmh):
        event = {
            "timestamp":       datetime.now().isoformat(),
            "intersection_id": intersection_id,
            "sensor_id":       sensor_id,
            "speed_kmh":       speed_kmh,
        }
        with self.lock:
            self.push_events.append(event)
            self._save()

    def add_mode_event(self, event_type, source="auto", **kwargs):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type":      event_type,
            "source":    source,
        }
        event.update(kwargs)
        with self.lock:
            self.mode_events.append(event)
            self._save()
