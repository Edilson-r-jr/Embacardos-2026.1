import random
import socket
import threading
import time

from common.messages import (
    create_heartbeat,
    create_vehicle_count,
    create_speed_violation
)


class TCPClient(threading.Thread):

    def __init__(
        self,
        host,
        port,
        intersection_id
    ):

        super().__init__(daemon=True)

        self.host = host
        self.port = port

        self.intersection_id = (
            intersection_id
        )

        self.socket = None

        self.sensor_1_count = 0
        self.sensor_2_count = 0

    def connect(self):

        while True:

            try:

                self.socket = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_STREAM
                )

                self.socket.connect(
                    (self.host, self.port)
                )

                print(
                    f"[DIST {self.intersection_id}] "
                    "Conectado"
                )

                return

            except Exception:

                print(
                    f"[DIST {self.intersection_id}] "
                    "Reconectando..."
                )

                time.sleep(2)

    def send_message(
        self,
        message
    ):

        self.socket.send(
            (message + "\n").encode()
        )

    def run(self):

        self.connect()

        last_heartbeat = 0
        last_count_update = 0

        while True:

            try:

                now = time.time()

                # Heartbeat
                if now - last_heartbeat >= 2:

                    self.send_message(
                        create_heartbeat(
                            self.intersection_id
                        )
                    )

                    last_heartbeat = now

                # Contagem de veículos
                if now - last_count_update >= 5:

                    self.sensor_1_count += (
                        random.randint(1, 5)
                    )

                    self.sensor_2_count += (
                        random.randint(1, 5)
                    )

                    self.send_message(
                        create_vehicle_count(
                            self.intersection_id,
                            1,
                            self.sensor_1_count
                        )
                    )

                    self.send_message(
                        create_vehicle_count(
                            self.intersection_id,
                            2,
                            self.sensor_2_count
                        )
                    )

                    last_count_update = now

                # Simulação de infração
                if random.random() < 0.03:

                    sensor = random.choice(
                        [1, 2]
                    )

                    speed = round(
                        random.uniform(
                            61,
                            100
                        ),
                        1
                    )

                    self.send_message(
                        create_speed_violation(
                            self.intersection_id,
                            sensor,
                            speed
                        )
                    )

                time.sleep(0.5)

            except Exception:

                print(
                    f"[DIST {self.intersection_id}] "
                    "Conexão perdida"
                )

                self.connect()