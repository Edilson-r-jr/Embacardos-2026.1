import json
import os
from datetime import datetime
import threading


class ViolationLogger:
    """
    Gerencia log persistente de violações (multas)
    Salva em arquivo JSON para persistência
    """
    
    LOG_FILE = "multas.json"
    
    def __init__(self):
        self.violations = []
        self.lock = threading.Lock()
        self.load_from_file()

    def add_violation(self, timestamp, intersection_id, sensor_id, speed_kmh, camera_modbus, plate, confidence, fine_value=0):
        """
        Registra uma violação
        """
        violation = {
            "timestamp": timestamp,
            "intersection_id": intersection_id,
            "sensor_id": sensor_id,
            "speed_kmh": speed_kmh,
            "camera_modbus": f"0x{camera_modbus:02X}",
            "plate": plate,
            "confidence": confidence,
            "fine_value": fine_value
        }
        
        with self.lock:
            self.violations.append(violation)
            self.save_to_file()

    def save_to_file(self):
        """Salva violações em arquivo"""
        try:
            with open(self.LOG_FILE, 'w') as f:
                json.dump(self.violations, f, indent=2, default=str)
        except Exception as e:
            print(f"Erro ao salvar log de multas: {e}")

    def load_from_file(self):
        """Carrega violações do arquivo"""
        try:
            if os.path.exists(self.LOG_FILE):
                with open(self.LOG_FILE, 'r') as f:
                    self.violations = json.load(f)
        except Exception as e:
            print(f"Erro ao carregar log de multas: {e}")
            self.violations = []

    def get_violations_by_intersection(self, intersection_id):
        """Retorna todas as violações de um cruzamento"""
        with self.lock:
            return [v for v in self.violations if v["intersection_id"] == intersection_id]

    def get_total_violations_by_intersection(self, intersection_id):
        """Retorna total de violações por cruzamento"""
        return len(self.get_violations_by_intersection(intersection_id))

    def get_total_fine_value_by_intersection(self, intersection_id):
        """Retorna valor total de multas por cruzamento"""
        violations = self.get_violations_by_intersection(intersection_id)
        return sum(v.get("fine_value", 0) for v in violations)

    def get_all_violations(self):
        """Retorna todas as violações"""
        with self.lock:
            return self.violations.copy()
