import time
import RPi.GPIO as GPIO

from constants import *
from gpio_controller import set_model1_state
from utils.logger import log

# =========================
# VARIÁVEIS
# =========================

pedestrian_request = False

# =========================
# CALLBACK
# =========================

def button_callback(channel):

    global pedestrian_request

    pedestrian_request = True

    if channel == M1_BUTTON_MAIN:

        log("[M1] Botão Pedestre Principal pressionado")

    elif channel == M1_BUTTON_CROSS:

        log("[M1] Botão Pedestre Cruzamento pressionado")

# =========================
# BOTÕES
# =========================

GPIO.add_event_detect(
    M1_BUTTON_MAIN,
    GPIO.RISING,
    callback=button_callback,
    bouncetime=200
)

GPIO.add_event_detect(
    M1_BUTTON_CROSS,
    GPIO.RISING,
    callback=button_callback,
    bouncetime=200
)

# =========================
# LOOP PRINCIPAL
# =========================

def run(stop_event):

    global pedestrian_request

    while not stop_event.is_set():

        # =====================
        # VERDE
        # =====================

        pedestrian_request = False

        log("[M1] Estado: VERDE")

        set_model1_state(0, 0, 1)

        start_time = time.time()

        while not stop_event.is_set():

            elapsed = time.time() - start_time

            # tempo máximo
            if elapsed >= M1_GREEN_TIME:

                log("[M1] Tempo máximo do verde atingido")

                break

            # mudança antecipada
            if pedestrian_request and elapsed >= M1_MIN_GREEN_TIME:

                log("[M1] Mudança antecipada por pedestre")

                break

            time.sleep(0.1)

        if stop_event.is_set():
            break

        # =====================
        # AMARELO
        # =====================

        log("[M1] Estado: AMARELO")

        set_model1_state(0, 1, 0)

        time.sleep(M1_YELLOW_TIME)

        if stop_event.is_set():
            break

        # =====================
        # VERMELHO
        # =====================

        log("[M1] Estado: VERMELHO")

        set_model1_state(1, 0, 0)

        time.sleep(M1_RED_TIME)

        if stop_event.is_set():
            break