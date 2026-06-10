import random
import socket
import threading
import time
import json

from common.messages import (
    create_heartbeat,
    create_vehicle_count,
    create_speed_violation
)

from distributed.constants import SPEED_VIOLATION_LIMIT


class TCPClient(threading.Thread):

    def __init__(
        self,
        host,
        port,
        intersection_id,
        traffic_state_machine=None
    ):

        super().__init__(daemon=True)

        self.host = host
        self.port = port

        self.intersection_id = intersection_id
        self.socket = None
        self.traffic_state_machine = traffic_state_machine

        self.sensor_1_count = 0
        self.sensor_2_count = 0
        self.speed_sensors = {}  # {sensor_id: SpeedSensorReader}
        self.running = True
        self.sensor_polling_thread = None

    def set_speed_sensors(self, sensors):
        """Define os sensores de velocidade para leitura"""
        self.speed_sensors = sensors

    def start_sensor_polling(self):
        """Inicia polling contínuo de sensores de velocidade"""
        if self.sensor_polling_thread is not None:
            return

        def polling_loop():
            while self.running:
                for sensor in self.speed_sensors.values():
                    try:
                        sensor.read_speed()
                    except Exception as e:
                        print(f"[DIST {self.intersection_id}] Erro no polling do sensor: {e}")
                time.sleep(0.01)

        self.sensor_polling_thread = threading.Thread(
            target=polling_loop,
            daemon=True
        )
        self.sensor_polling_thread.start()

    def connect(self):
        # Fecha socket anterior antes de criar um novo
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
                self.socket = sock  # só atribui após conexão bem-sucedida
                print(f"[DIST {self.intersection_id}] Conectado")
                return
            except Exception:
                print(f"[DIST {self.intersection_id}] Reconectando...")
                try:
                    sock.close()
                except Exception:
                    pass
                time.sleep(2)

    def send_message(self, message):
        try:
            self.socket.send((message + "\n").encode())
        except Exception as e:
            print(f"[DIST {self.intersection_id}] Erro ao enviar: {e}")
            self.socket = None  # sinaliza desconexão para o loop principal

    def receive_commands(self):
        """Thread que recebe comandos do central.
        Não reconecta — apenas sinaliza a queda para o loop run()."""
        buffer = ""

        while self.running:
            sock = self.socket  # captura local para evitar race condition
            if not sock:
                time.sleep(0.1)
                continue
            try:
                sock.settimeout(0.5)
                try:
                    data = sock.recv(1024)
                    if not data:
                        print(f"[DIST {self.intersection_id}] Conexão fechada pelo servidor")
                        if self.socket is sock:
                            self.socket = None
                        buffer = ""
                        continue
                    buffer += data.decode()
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if line:
                            self.process_command(line)
                except socket.timeout:
                    pass
            except Exception as e:
                print(f"[DIST {self.intersection_id}] Erro ao receber: {e}")
                if self.socket is sock:
                    self.socket = None
                buffer = ""

            time.sleep(0.1)

    def process_command(self, command_str):
        """Processa comando recebido do servidor central"""
        try:
            cmd = json.loads(command_str)
            cmd_type = cmd.get("type")
            
            if cmd_type == "night_mode":
                enabled = cmd.get("enabled", False)
                if self.traffic_state_machine:
                    self.traffic_state_machine.set_night_mode(enabled)
                    print(f"[DIST {self.intersection_id}] Modo noturno: {enabled}")
            
            elif cmd_type == "emergency":
                active = cmd.get("active", False)
                signal_group = cmd.get("signal_group", 0)
                if self.traffic_state_machine:
                    self.traffic_state_machine.set_emergency(active, signal_group)
                    print(f"[DIST {self.intersection_id}] Emergência: {active}, grupo: {signal_group}")

            elif cmd_type == "manual_override":
                state_code = cmd.get("state_code")
                if self.traffic_state_machine:
                    self.traffic_state_machine.set_manual_override(state_code)
                    label = "retomar normal" if state_code is None else f"código={state_code}"
                    print(f"[DIST {self.intersection_id}] Controle manual: {label}")
            
        except Exception as e:
            print(f"[DIST {self.intersection_id}] Erro ao processar comando: {e}")

    def run(self):
        if self.speed_sensors:
            self.start_sensor_polling()

        # Thread de recebimento apenas sinaliza a queda; run() reconecta
        threading.Thread(target=self.receive_commands, daemon=True).start()

        last_heartbeat = 0
        last_count_update = 0

        while self.running:
            # Único ponto de reconexão: detecta socket None e reconecta
            if not self.socket:
                self.connect()
                last_heartbeat = 0  # força heartbeat imediato após reconexão
                if not self.socket:
                    time.sleep(0.5)
                    continue

            try:
                now = time.time()

                # Heartbeat
                if now - last_heartbeat >= 2:
                    self.send_message(create_heartbeat(self.intersection_id))
                    last_heartbeat = now

                # Leitura de velocidade e infrações reais
                if self.speed_sensors:
                    for sensor_id, sensor in self.speed_sensors.items():
                        speed = sensor.pop_last_speed()
                        if speed is not None and speed > SPEED_VIOLATION_LIMIT:
                            self.send_message(
                                create_speed_violation(
                                    self.intersection_id,
                                    sensor_id,
                                    round(speed, 1)
                                )
                            )

                # Contagem de veículos (envia cumulativo)
                if now - last_count_update >= 2:
                    if self.speed_sensors:
                        for sensor_id, sensor in self.speed_sensors.items():
                            count = sensor.get_vehicle_count()
                            if count > 0:
                                self.send_message(
                                    create_vehicle_count(
                                        self.intersection_id,
                                        sensor_id,
                                        count
                                    )
                                )
                    else:
                        # Simulação (fallback) — usa IDs corretos por cruzamento
                        self.sensor_1_count += random.randint(1, 5)
                        self.sensor_2_count += random.randint(1, 5)
                        if self.intersection_id == 1:
                            sid_a, sid_b = 1, 2
                        else:
                            sid_a, sid_b = 3, 4
                        self.send_message(
                            create_vehicle_count(self.intersection_id, sid_a, self.sensor_1_count)
                        )
                        self.send_message(
                            create_vehicle_count(self.intersection_id, sid_b, self.sensor_2_count)
                        )
                    last_count_update = now

                # Simulação de infração apenas se não há sensores reais disponíveis
                if not self.speed_sensors and random.random() < 0.03:
                    sensor = random.choice([1, 2])
                    speed = round(random.uniform(61, 100), 1)
                    self.send_message(
                        create_speed_violation(self.intersection_id, sensor, speed)
                    )

                time.sleep(0.5)

            except Exception as e:
                print(f"[DIST {self.intersection_id}] Erro: {e}")
    
    def stop(self):
        """Para o cliente"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
