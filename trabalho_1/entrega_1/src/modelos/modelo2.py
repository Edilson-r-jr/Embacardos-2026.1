import time
import RPi.GPIO as GPIO

from constants import *
from gpio_controller import set_model2_state

# =========================
# VARIÁVEIS
# =========================

main_request = False
cross_request = False

# =========================
# CALLBACK DOS BOTÕES
# =========================

def button_callback(channel):

    global main_request
    global cross_request

    if channel == M2_BUTTON_MAIN:

        main_request = True

        print("[M2] Botão Pedestre Principal pressionado")

    elif channel == M2_BUTTON_CROSS:

        cross_request = True

        print("[M2] Botão Pedestre Cruzamento pressionado")

# =========================
# INTERRUPÇÕES
# =========================

GPIO.add_event_detect(
    M2_BUTTON_MAIN,
    GPIO.RISING,
    callback=button_callback,
    bouncetime=200
)

GPIO.add_event_detect(
    M2_BUTTON_CROSS,
    GPIO.RISING,
    callback=button_callback,
    bouncetime=200
)

# =========================
# LOOP PRINCIPAL
# =========================

def run():

    global main_request
    global cross_request

    while True:

        # ==================================================
        # ESTADO 1
        # Principal Verde / Cruzamento Vermelho
        # ==================================================

        print("\n[M2] Estado 1")

        set_model2_state(1)

        main_request = False

        start_time = time.time()

        while True:

            elapsed = time.time() - start_time

            # tempo máximo atingido
            if elapsed >= M2_MAIN_GREEN_MAX:

                print("[M2] Tempo máximo principal atingido")

                break

            # pedestre solicitou após mínimo
            if main_request and elapsed >= M2_MAIN_GREEN_MIN:

                print("[M2] Mudança antecipada principal")

                break

            time.sleep(0.1)

        # ==================================================
        # ESTADO 2
        # Principal Amarelo
        # ==================================================

        print("\n[M2] Estado 2")

        set_model2_state(2)

        time.sleep(M2_YELLOW_TIME)

        # ==================================================
        # ESTADO 4
        # Tudo Vermelho
        # ==================================================

        print("\n[M2] Estado 4")

        set_model2_state(4)

        time.sleep(M2_ALL_RED_TIME)

        # ==================================================
        # ESTADO 5
        # Cruzamento Verde
        # ==================================================

        print("\n[M2] Estado 5")

        set_model2_state(5)

        cross_request = False

        start_time = time.time()

        while True:

            elapsed = time.time() - start_time

            # tempo máximo atingido
            if elapsed >= M2_CROSS_GREEN_MAX:

                print("[M2] Tempo máximo cruzamento atingido")

                break

            # pedestre solicitou após mínimo
            if cross_request and elapsed >= M2_CROSS_GREEN_MIN:

                print("[M2] Mudança antecipada cruzamento")

                break

            time.sleep(0.1)

        # ==================================================
        # ESTADO 6
        # Cruzamento Amarelo
        # ==================================================

        print("\n[M2] Estado 6")

        set_model2_state(6)

        time.sleep(M2_YELLOW_TIME)

        # ==================================================
        # ESTADO 4
        # Tudo Vermelho
        # ==================================================

        print("\n[M2] Estado 4")

        set_model2_state(4)

        time.sleep(M2_ALL_RED_TIME)