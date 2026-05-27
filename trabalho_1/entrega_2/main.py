from simplified_protocol import *
from modbus_protocol import *

while True:

    print("\n========== UART ==========")
    print("1 - Simplificado")
    print("2 - MODBUS")
    print("0 - Sair")

    protocolo = input("> ")

    # ======================
    # SIMPLIFICADO
    # ======================

    if protocolo == "1":

        print("\n1 - Solicitar inteiro")
        print("2 - Solicitar float")
        print("3 - Solicitar string")
        print("4 - Enviar inteiro")
        print("5 - Enviar float")
        print("6 - Enviar string")

        op = input("> ")

        if op == "1":
            solicitar_inteiro()

        elif op == "2":
            solicitar_float()

        elif op == "3":
            solicitar_string()

        elif op == "4":
            valor = int(input("Valor: "))
            enviar_inteiro(valor)

        elif op == "5":
            valor = float(input("Valor: "))
            enviar_float(valor)

        elif op == "6":
            texto = input("Texto: ")
            enviar_string(texto)

    # ======================
    # MODBUS
    # ======================

    elif protocolo == "2":

        print("\n1 - Solicitar inteiro")
        print("2 - Solicitar float")
        print("3 - Solicitar string")
        print("4 - Enviar inteiro")
        print("5 - Enviar float")
        print("6 - Enviar string")

        op = input("> ")

        if op == "1":
            solicitar_int_modbus()

        elif op == "2":
            solicitar_float_modbus()

        elif op == "3":
            solicitar_string_modbus()

        elif op == "4":
            valor = int(input("Valor: "))
            enviar_int_modbus(valor)

        elif op == "5":
            valor = float(input("Valor: "))
            enviar_float_modbus(valor)

        elif op == "6":
            texto = input("Texto: ")
            enviar_string_modbus(texto)