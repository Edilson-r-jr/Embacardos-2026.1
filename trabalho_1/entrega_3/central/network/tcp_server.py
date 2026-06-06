import socket
import threading

from common.messages import parse_message


class TCPServer:

    def __init__(
        self,
        state_manager,
        host="0.0.0.0",
        port=5000
    ):

        self.host = host
        self.port = port

        self.state_manager = (
            state_manager
        )

        self.server_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

    def start(self):

        self.server_socket.bind(
            (self.host, self.port)
        )

        self.server_socket.listen()

        print(
            f"[CENTRAL] Escutando "
            f"{self.host}:{self.port}"
        )

        while True:

            client_socket, address = (
                self.server_socket.accept()
            )

            print(
                f"[CENTRAL] Nova conexão "
                f"{address}"
            )

            threading.Thread(
                target=self.handle_client,
                args=(client_socket,),
                daemon=True
            ).start()

    def handle_client(
    self,
    client_socket
    ):

        buffer = ""

        while True:

            try:

                data = client_socket.recv(
                    1024
                )

                if not data:
                    break

                buffer += data.decode()

                while "\n" in buffer:

                    line, buffer = (
                        buffer.split(
                            "\n",
                            1
                        )
                    )

                    if not line:
                        continue

                    message = parse_message(
                        line
                    )

                    self.state_manager.process_message(
                        message
                    )

            except Exception as e:

                print(
                    "[CENTRAL] Erro:",
                    e
                )

                break

        client_socket.close()