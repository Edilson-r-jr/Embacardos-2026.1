import json
import os
import threading
import time
from datetime import datetime

CMD_FILE = "central_cmd.json"

from central.network.tcp_server import TCPServer
from central.state.state_manager import StateManager
from central.modbus.emergency_reader import EmergencyReader
from central.modbus.lpr_camera import LPRCamera
from central.violations_logger import ViolationLogger
from central.events_logger import EventsLogger
from central.constants import (
    SENSOR_TO_CAMERA, SPEED_VIOLATION_LIMIT, FINE_VALUE, UART_PORT
)


class CentralManager:
    """Gerenciador central do sistema"""
    
    def __init__(self):

        self.modbus_lock = threading.Lock()

        # Componentes principais
        self.state_manager = None
        self.server = None
        self.emergency_reader = None
        self.violations_logger = ViolationLogger()
        self.events_logger = EventsLogger()
        self.lpr_cameras = {}
        
        # Estado de emergência
        self.last_emergency_state = None
        self.emergency_command_sent = {}  # Rastreia comandos de emergência
        
        # Modo noturno
        self.night_mode_active = False
        self.night_mode_last_toggle = 0
        self.night_mode_manual_override = False  # True = ignora MODBUS para night mode

    def on_new_connection(self, intersection_id):
        """Reenvia estado salvo para um novo cruzamento conectado"""
        if self.state_manager.is_night_mode():
            command = {
                "type": "night_mode",
                "enabled": True
            }
            self.server.send_command_to_intersection(intersection_id, command)

        if self.state_manager.is_emergency_active():
            emergency_state = self.state_manager.get_emergency_state()
            if emergency_state and self._is_intersection_affected(intersection_id, emergency_state):
                command = {
                    "type": "emergency",
                    "active": emergency_state.get("active", False),
                    "road": emergency_state.get("road"),
                    "signal_group": emergency_state.get("signal_group")
                }
                self.server.send_command_to_intersection(intersection_id, command)

    def _is_intersection_affected(self, intersection_id, emergency_state):
        if emergency_state["intersection_id"] == 0:
            return True
        return emergency_state["intersection_id"] == intersection_id
        
    def initialize(self):
        """Inicializa todos os componentes"""
        print("[CENTRAL] Inicializando...")
        
        # Cria state manager com callback de violações
        self.state_manager = StateManager(
            violation_callback=self.handle_speed_violation
        )
        
        # Inicia servidor TCP
        self.server = TCPServer(
            self.state_manager,
            new_connection_callback=self.on_new_connection
        )
        threading.Thread(
            target=self.server.start,
            daemon=True
        ).start()

        # Restaura estados salvos
        self.night_mode_active = self.state_manager.is_night_mode()
        self.last_emergency_state = self.state_manager.is_emergency_active()
        
        # Inicia leitor de emergências
        self.emergency_reader = EmergencyReader(port=UART_PORT)
        self.emergency_reader.start()
        
        # Inicializa câmeras LPR
        for sensor_id, camera_addr in SENSOR_TO_CAMERA.items():
            self.lpr_cameras[sensor_id] = LPRCamera(
                address=camera_addr,
                port=UART_PORT
            )
        
        print("[CENTRAL] Sistema iniciado")
    
    def handle_speed_violation(self, intersection_id, sensor_id, speed_kmh):
        self.events_logger.add_push_event(intersection_id, sensor_id, speed_kmh)

        if sensor_id in SENSOR_TO_CAMERA:
            self.trigger_lpr_camera(intersection_id, sensor_id, speed_kmh)
    
    def trigger_lpr_camera(self, intersection_id, sensor_id, speed_kmh):
        if sensor_id not in self.lpr_cameras:
            return

        camera = self.lpr_cameras[sensor_id]

        with self.modbus_lock:
            plate, confidence = camera.trigger_capture()

        if plate and confidence is not None:
            timestamp = datetime.now().isoformat()
            camera_addr = SENSOR_TO_CAMERA[sensor_id]

            self.events_logger.add_lpr_event(intersection_id, sensor_id, plate, confidence)

            self.violations_logger.add_violation(
                timestamp=timestamp,
                intersection_id=intersection_id,
                sensor_id=sensor_id,
                speed_kmh=speed_kmh,
                camera_modbus=camera_addr,
                plate=plate,
                confidence=confidence,
                fine_value=FINE_VALUE
            )
    
    def handle_emergency(self, emergency_state):
        if not emergency_state:
            return

        active = bool(emergency_state["active"])

        # Emergência iniciou
        if active and not self.last_emergency_state:
            self.events_logger.add_mode_event(
                "emergency", source="modbus", active=True,
                road=emergency_state.get("road"),
                signal_group=emergency_state.get("signal_group"),
                intersection_id=emergency_state.get("intersection_id"),
            )
            self.send_emergency_command(emergency_state)
            self.state_manager.set_emergency_active(True)
            self.state_manager.set_emergency_state(emergency_state)
            self.last_emergency_state = True

        # Emergência terminou
        elif not active and self.last_emergency_state:
            self.events_logger.add_mode_event("emergency", source="modbus", active=False)
            self.clear_emergency_command()
            self.state_manager.set_emergency_active(False)
            self.state_manager.set_emergency_state(emergency_state)
            self.last_emergency_state = False

        # Permanece ativa: apenas atualiza o último payload
        elif active:
            self.state_manager.set_emergency_state(emergency_state)
    
    def send_emergency_command(self, emergency_state):
        """Envia comando de emergência para cruzamentos"""
        intersection_ids = []
        
        # Determina quais cruzamentos são afetados
        if emergency_state['intersection_id'] == 0:
            # Afeta todos
            intersection_ids = [1, 2]
        else:
            # Afeta apenas um
            intersection_ids = [emergency_state['intersection_id']]
        
        for inter_id in intersection_ids:
            # Envia para servidor distribuído
            if self.server:
                # Monta comando de emergência
                command = {
                    "type": "emergency",
                    "active": emergency_state['active'],
                    "road": emergency_state['road'],
                    "signal_group": emergency_state['signal_group']
                }
                
                self.server.send_command_to_intersection(inter_id, command)
    
    def handle_night_mode(self, emergency_state):
        if not emergency_state:
            return

        if self.night_mode_manual_override:
            return

        night_mode = bool(emergency_state.get('night_mode', 0))

        if night_mode != self.night_mode_active:
            self.night_mode_active = night_mode
            self.state_manager.set_night_mode(night_mode)

            self.events_logger.add_mode_event("night_mode", source="modbus", enabled=night_mode)

            if self.server:
                command = {
                    "type": "night_mode",
                    "enabled": night_mode
                }
                self.server.send_command_to_intersection(1, command)
                self.server.send_command_to_intersection(2, command)
    
    def polling_emergency(self):
        while True:
            try:
                if self.emergency_reader:
                    with self.modbus_lock:
                        state = self.emergency_reader.get_state()

                    if state:
                        self.handle_emergency(state)
                        self.handle_night_mode(state)

            except Exception as e:
                print(f"[CENTRAL] Erro no polling de emergência: {e}")

            time.sleep(0.5)
    
    def clear_emergency_command(self): #clear_emergency_command encerrar o modo de emergência em todos os cruzamentos"""
        if not self.server:
            return

        command = {
            "type": "emergency",
            "active": False,
            "road": 0,
            "signal_group": 0
        }

        # Envia para ambos para garantir limpeza do estado
        self.server.send_command_to_intersection(1, command)
        self.server.send_command_to_intersection(2, command)

    def _poll_commands(self):
        while True:
            try:
                if os.path.exists(CMD_FILE):
                    with open(CMD_FILE, "r", encoding="utf-8") as f:
                        cmd = json.load(f)
                    os.remove(CMD_FILE)
                    self._execute_command(cmd)
            except Exception as e:
                print(f"[CENTRAL] Erro ao ler comando manual: {e}")
            time.sleep(0.3)

    def _execute_command(self, cmd):
        cmd_type = cmd.get("type")

        if cmd_type == "night_mode":
            enabled = cmd.get("enabled", False)
            self.night_mode_active = enabled
            self.night_mode_manual_override = enabled
            self.state_manager.set_night_mode(enabled)
            self.events_logger.add_mode_event("night_mode", source="manual", enabled=enabled)
            if self.server:
                command = {"type": "night_mode", "enabled": enabled}
                self.server.send_command_to_intersection(1, command)
                self.server.send_command_to_intersection(2, command)

        elif cmd_type == "manual_override":
            iid        = cmd.get("intersection_id")
            state_code = cmd.get("state_code")
            if self.server and iid:
                self.server.send_command_to_intersection(
                    iid, {"type": "manual_override", "state_code": state_code}
                )

    def run(self):
        """Executa o sistema central"""
        self.initialize()

        threading.Thread(target=self.polling_emergency, daemon=True).start()
        threading.Thread(target=self._poll_commands, daemon=True).start()

        # Mantém o processo vivo
        while True:
            time.sleep(1)
    
    def shutdown(self):
        """Desliga o sistema"""
        if self.emergency_reader:
            self.emergency_reader.stop()
        


def main():
    central = CentralManager()
    
    try:
        central.run()
    except KeyboardInterrupt:
        print("\n[CENTRAL] Desligando...")
        central.shutdown()


if __name__ == "__main__":
    main()
