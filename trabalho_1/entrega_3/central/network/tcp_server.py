import socket
import threading
import json

from common.messages import parse_message


class TCPServer:

    def __init__(
        self,
        state_manager,
        host="0.0.0.0",
        port=5000,
        new_connection_callback=None
    ):

        self.host = host
        self.port = port

        self.state_manager = (
            state_manager
        )
        self.new_connection_callback = new_connection_callback

        self.server_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        
        # Rastreia clientes por intersection_id
        self.client_sockets = {}
        self.client_lock = threading.Lock()

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

            try:
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
            except Exception as e:
                print(f"[CENTRAL] Erro ao aceitar conexão: {e}")

    def handle_client(self, client_socket):

        buffer = ""
        intersection_id = None

        while True:

            try:

                data = client_socket.recv(1024)

                if not data:
                    break

                buffer += data.decode()

                while "\n" in buffer:

                    line, buffer = (
                        buffer.split("\n", 1)
                    )

                    if not line:
                        continue

                    try:
                        message = parse_message(line)
                        
                        # Rastreia intersection_id na primeira mensagem
                        if intersection_id is None and "intersection_id" in message:
                            intersection_id = message["intersection_id"]
                            with self.client_lock:
                                self.client_sockets[intersection_id] = client_socket
                            print(f"[CENTRAL] Registrado cruzamento {intersection_id}")

                            if self.new_connection_callback:
                                try:
                                    self.new_connection_callback(intersection_id)
                                except Exception as callback_error:
                                    print(f"[CENTRAL] Erro no callback de nova conexão: {callback_error}")

                        self.state_manager.process_message(message)
                    except Exception as e:
                        print(f"[CENTRAL] Erro ao processar mensagem: {e}")

            except Exception as e:

                print(
                    "[CENTRAL] Erro:",
                    e
                )

                break

        # Remove cliente
        if intersection_id:
            with self.client_lock:
                if intersection_id in self.client_sockets:
                    del self.client_sockets[intersection_id]
                    print(f"[CENTRAL] Desconectado cruzamento {intersection_id}")

        client_socket.close()
    
    def send_command_to_intersection(self, intersection_id, command):
        """Envia comando para um cruzamento específico"""
        with self.client_lock:
            if intersection_id not in self.client_sockets:
                print(f"[CENTRAL] Cruzamento {intersection_id} não conectado")
                return False
            
            try:
                client = self.client_sockets[intersection_id]
                message = json.dumps(command) + "\n"
                client.send(message.encode())
                return True
            except Exception as e:
                print(f"[CENTRAL] Erro ao enviar comando: {e}")
                return False
