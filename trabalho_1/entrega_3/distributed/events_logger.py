import json
import os
import threading
from datetime import datetime


class DistEventLogger:

    def __init__(self, intersection_id):
        self.log_file = f"logs/dist{intersection_id}_events.json"
        self.lock     = threading.Lock()
        self.messages = []
        self.commands = []
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.messages = data.get("messages", [])
                self.commands = data.get("commands",  [])
        except Exception:
            pass

    def _save(self):
        try:
            os.makedirs("logs", exist_ok=True)
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump({
                    "messages": self.messages,
                    "commands": self.commands,
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"[DIST] Erro ao salvar events log: {e}")

    def add_message(self, msg_type, sensor_id=None, value=None):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type":      msg_type,
            "sensor_id": sensor_id,
            "value":     value,
        }
        with self.lock:
            self.messages.append(event)
            self._save()

    def add_command(self, cmd_type, data=None):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type":      cmd_type,
            "data":      data or {},
        }
        with self.lock:
            self.commands.append(event)
            self._save()
