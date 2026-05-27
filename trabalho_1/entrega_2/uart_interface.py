import serial
import time


ser = serial.Serial(

    port="/dev/serial0",
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)


def send_packet(packet):

    # limpa buffers antigos
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # envia pacote
    ser.write(packet)

    # garante envio imediato
    ser.flush()

    # pequeno delay para ESP32 responder
    time.sleep(0.1)


def read_packet(size):

    response = ser.read(size)

    return response


def close_uart():

    ser.close()