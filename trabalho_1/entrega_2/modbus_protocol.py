from urllib import response

from uart_interface import send_packet, read_packet
from utils import *
from crc16 import append_crc

ENDERECO = 0x01

FUNCAO_LEITURA = 0x23
FUNCAO_ESCRITA = 0x16


# =====================================================
# AUXILIAR
# =====================================================

def check_modbus_error(response):

    if len(response) >= 3:

        funcao = response[0]

        if funcao & 0x80:

            print("Erro MODBUS")
            print(f"Código da exceção: 0x{response[1]:02X}")

            return True

    return False


# =====================================================
# SOLICITA INTEIRO
# =====================================================

def solicitar_int_modbus():

    packet = bytes([
        ENDERECO,
        FUNCAO_LEITURA,
        0xA1
    ]) + MATRICULA

    packet = append_crc(packet)

    print_hex("TX", packet)

    send_packet(packet)

    response = read_packet(7)

    print_hex("RX", response)

    if len(response) != 7:
        print("Timeout")
        return

    if check_modbus_error(response):
        return

    dados = response[3:7]

    value = unpack_int(dados)

    print("Inteiro:", value)


# =====================================================
# SOLICITA FLOAT
# =====================================================

def solicitar_float_modbus():

    packet = bytes([
        ENDERECO,
        FUNCAO_LEITURA,
        0xA2
    ]) + MATRICULA

    packet = append_crc(packet)

    print_hex("TX", packet)

    send_packet(packet)

    response = read_packet(7)

    print_hex("RX", response)

    if len(response) != 7:
        print("Timeout")
        return

    dados = response[3:7]

    value = unpack_float(dados)

    print("Float:", value)


# =====================================================
# SOLICITA STRING
# =====================================================

def solicitar_string_modbus():

    packet = bytes([
        ENDERECO,
        FUNCAO_LEITURA,
        0xA3
    ]) + MATRICULA

    packet = append_crc(packet)

    print_hex("TX", packet)

    send_packet(packet)

    response = read_packet(64)

    print_hex("RX", response)

    if len(response) < 4:
        print("Timeout")
        return

    tamanho = response[3]

    dados = response[4:4+tamanho]

    try:
        texto = dados.decode()

    except:
        texto = dados.decode(errors="ignore")

    print("String:", texto)


# =====================================================
# ENVIA INTEIRO
# =====================================================

def enviar_int_modbus(valor):

    packet = (
        bytes([
            ENDERECO,
            FUNCAO_ESCRITA,
            0xB1
        ]) +
        pack_int(valor) +
        MATRICULA
    )

    packet = append_crc(packet)

    print_hex("TX", packet)

    send_packet(packet)

    response = read_packet(7)

    print_hex("RX", response)

    if len(response) != 7:
        print("Timeout")
        return

    dados = response[3:7]

    result = unpack_int(dados)

    print("Resultado:", result)


# =====================================================
# ENVIA FLOAT
# =====================================================

def enviar_float_modbus(valor):

    packet = (
        bytes([
            ENDERECO,
            FUNCAO_ESCRITA,
            0xB2
        ]) +
        pack_float(valor) +
        MATRICULA
    )

    packet = append_crc(packet)

    print_hex("TX", packet)

    send_packet(packet)

    response = read_packet(7)

    print_hex("RX", response)

    if len(response) != 7:
        print("Timeout")
        return

    dados = response[3:7]

    result = unpack_float(dados)

    print("Resultado:", result)


# =====================================================
# ENVIA STRING
# =====================================================

def enviar_string_modbus(texto):

    texto_bytes = texto.encode()

    packet = (
        bytes([
            ENDERECO,
            FUNCAO_ESCRITA,
            0xB3,
            len(texto_bytes)
        ]) +
        texto_bytes +
        MATRICULA
    )

    packet = append_crc(packet)

    print_hex("TX", packet)

    send_packet(packet)

    response = read_packet(128)

    print_hex("RX", response)

    if len(response) < 4:
        print("Timeout")
        return

    tamanho = response[3]

    dados = response[4:4+tamanho]

    try:
        texto = dados.decode()

    except:
        texto = dados.decode(errors="ignore")

    print("String:", texto)