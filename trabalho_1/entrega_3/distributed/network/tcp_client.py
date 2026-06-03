import socket
import time

from common.messages import (
    create_heartbeat
)


class TCPClient:

    def __init__(
        self,
        host,
        port,
        intersection_id
    ):

        self.host = host
        self.port = port

        self.intersection_id = (
            intersection_id
        )

        self.socket = None

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
                    "[DIST] Conectado "
                    "ao Central"
                )

                return

            except Exception:

                print(
                    "[DIST] Tentando "
                    "reconectar..."
                )

                time.sleep(2)

    def send_heartbeat(self):

        while True:

            try:

                message = create_heartbeat(
                    self.intersection_id
                )

                self.socket.send(
                    message.encode()
                )

                print(
                    f"[DIST {self.intersection_id}] "
                    "Heartbeat enviado"
                )

                time.sleep(2)

            except Exception:

                print(
                    "[DIST] Conexão perdida"
                )

                self.connect()