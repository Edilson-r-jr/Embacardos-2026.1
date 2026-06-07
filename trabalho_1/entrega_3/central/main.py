import threading
import time
from datetime import datetime

from central.network.tcp_server import TCPServer
from central.state.state_manager import StateManager
from central.modbus.emergency_reader import EmergencyReader
from central.modbus.lpr_camera import LPRCamera
from central.violations_logger import ViolationLogger
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
        self.lpr_cameras = {}
        
        # Estado de emergência
        self.last_emergency_state = None
        self.emergency_command_sent = {}  # Rastreia comandos de emergência
        
        # Modo noturno
        self.night_mode_active = False
        self.night_mode_last_toggle = 0

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
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(
            f"[{timestamp}] "
            f"[PUSH] Infração recebida | "
            f"Cruzamento={intersection_id} "
            f"Sensor={sensor_id} "
            f"Velocidade={speed_kmh:.1f} km/h"
        )
        
        # Dispara câmera LPR correspondente
        if sensor_id in SENSOR_TO_CAMERA:
            self.trigger_lpr_camera(intersection_id, sensor_id, speed_kmh)
    
    def trigger_lpr_camera(self, intersection_id, sensor_id, speed_kmh):
        if sensor_id not in self.lpr_cameras:
            return

        camera = self.lpr_cameras[sensor_id]

        print(f"[LPR] Disparando câmera para sensor {sensor_id}...")

        with self.modbus_lock:
            plate, confidence = camera.trigger_capture()

        if plate and confidence is not None:
            timestamp = datetime.now().isoformat()
            camera_addr = SENSOR_TO_CAMERA[sensor_id]

            print(f"[LPR] Placa capturada: {plate} (confiança: {confidence}%)")

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

        active = emergency_state['active']

        # Emergência ativada
        if active:
            self.send_emergency_command(emergency_state)
            self.state_manager.set_emergency_active(True)
            self.state_manager.set_emergency_state(emergency_state)
            self.last_emergency_state = True

        # Emergência finalizada
        else:
            print("[EMERGENCY] Emergência finalizada")

            self.state_manager.set_emergency_active(False)
            self.state_manager.set_emergency_state(emergency_state)
            self.last_emergency_state = False
    
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

        night_mode = bool(emergency_state.get('night_mode', 0))

        if night_mode != self.night_mode_active:
            self.night_mode_active = night_mode
            self.state_manager.set_night_mode(night_mode)

            print(f"[NIGHT MODE] {'Ativado' if night_mode else 'Desativado'}")

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
    
    def dashboard_loop(self):
        """Loop de dashboard de monitoramento"""
        while True:
            try:
                print("\n" * 3)
                print("=" * 70)
                print("CENTRAL DE MONITORAMENTO")
                print("=" * 70)
                
                snapshot = self.state_manager.get_snapshot()
                
                for intersection in snapshot.values():
                    print()
                    print(f"Cruzamento {intersection.intersection_id}")
                    print("-" * 70)
                    
                    status = (
                        "ONLINE" if intersection.is_online() else "OFFLINE"
                    )
                    print(f"  Status: {status}")
                    
                    heartbeat = intersection.seconds_since_heartbeat()
                    if heartbeat is None:
                        print(f"  Heartbeat: nunca")
                    else:
                        print(f"  Heartbeat: {heartbeat}s")
                    
                    # Calcula fluxo de tráfego por sensor
                    if intersection.vehicle_count:
                        for sensor_id, count in sorted(
                            intersection.vehicle_count.items(),
                            key=lambda x: int(x[0])
                        ):
                            print(f"  Sensor {sensor_id}: {count} veículos")
                    else:
                        print("  Nenhum dado de sensor disponível")
                    
                    # Violações
                    violations = self.violations_logger.get_violations_by_intersection(
                        intersection.intersection_id
                    )
                    total_fines = self.violations_logger.get_total_fine_value_by_intersection(
                        intersection.intersection_id
                    )
                    
                    print(f"  Infrações: {intersection.speed_violations}")
                    print(f"  Multas Registradas: {len(violations)}")
                    if total_fines > 0:
                        print(f"  Valor Total: R$ {total_fines:.2f}")
                
                print()
                print("=" * 70)
                print(f"  Modo Noturno: {'SIM' if self.night_mode_active else 'NÃO'}")
                if self.last_emergency_state:
                    print(f"  Emergência: ATIVA")
                print("=" * 70)
                
                time.sleep(2)
            except Exception as e:
                print(f"[CENTRAL] Erro no dashboard: {e}")
                time.sleep(2)
    
    def run(self):
        """Executa o sistema central"""
        self.initialize()
        
        # Inicia thread de polling de emergência
        threading.Thread(
            target=self.polling_emergency,
            daemon=True
        ).start()
        
        # Inicia dashboard
        self.dashboard_loop()
    
    def shutdown(self):
        """Desliga o sistema"""
        if self.emergency_reader:
            self.emergency_reader.stop()
        
        for camera in self.lpr_cameras.values():
            camera.close()


def main():
    central = CentralManager()
    
    try:
        central.run()
    except KeyboardInterrupt:
        print("\n[CENTRAL] Desligando...")
        central.shutdown()


if __name__ == "__main__":
    main()
