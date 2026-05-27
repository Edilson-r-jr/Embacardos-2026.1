from uart_interface import send_packet, read_packet
from utils import *

# =========================
# SOLICITAÇÕES
# =========================

def solicitar_inteiro():

    packet = bytes([0xA1]) + MATRICULA

    print_hex("TX", packet)

    send_packet(packet)

    response = read_packet(4)

    print_hex("RX", response)

    if len(response) != 4:
        print("Timeout")
        return

    value = unpack_int(response)

    print("Inteiro:", value)

def solicitar_float():

    packet = bytes([0xA2]) + MATRICULA

    print_hex("TX", packet)

    send_packet(packet)

    response = read_packet(4)

    print_hex("RX", response)

    if len(response) != 4:
        print("Timeout")
        return

    value = unpack_float(response)

    print("Float:", value)

def solicitar_string():

    packet = bytes([0xA3]) + MATRICULA

    print_hex("TX", packet)

    send_packet(packet)

    size = read_packet(1)

    if len(size) != 1:
        print("Timeout")
        return

    size = size[0]

    response = read_packet(size)

    print_hex("RX", response)

    print("String:", response.decode())

# =========================
# ENVIOS
# =========================

def enviar_inteiro(valor):

    packet = (
        bytes([0xB1]) +
        pack_int(valor) +
        MATRICULA
    )

    print_hex("TX", packet)

    send_packet(packet)

    response = read_packet(4)

    print_hex("RX", response)

    result = unpack_int(response)

    print("Resultado:", result)

def enviar_float(valor):

    packet = (
        bytes([0xB2]) +
        pack_float(valor) +
        MATRICULA
    )

    print_hex("TX", packet)

    send_packet(packet)

    response = read_packet(4)

    print_hex("RX", response)

    result = unpack_float(response)

    print("Resultado:", result)

def enviar_string(texto):

    texto_bytes = texto.encode()

    packet = (
        bytes([0xB3]) +
        bytes([len(texto_bytes)]) +
        texto_bytes +
        MATRICULA
    )

    print_hex("TX", packet)

    send_packet(packet)

    size = read_packet(1)

    if len(size) != 1:
        print("Timeout")
        return

    size = size[0]

    response = read_packet(size)

    print_hex("RX", response)

    print(response.decode())