import RPi.GPIO as GPIO

from constants import *

# =========================
# GPIO SETUP
# =========================

GPIO.setmode(GPIO.BCM)

# LEDs Modelo 1
GPIO.setup(M1_GREEN_LED, GPIO.OUT)
GPIO.setup(M1_YELLOW_LED, GPIO.OUT)
GPIO.setup(M1_RED_LED, GPIO.OUT)

# Botões Modelo 1
GPIO.setup(M1_BUTTON_MAIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(M1_BUTTON_CROSS, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# =========================
# FUNÇÕES
# =========================

def set_model1_state(red, yellow, green):

    GPIO.output(M1_RED_LED, red)
    GPIO.output(M1_YELLOW_LED, yellow)
    GPIO.output(M1_GREEN_LED, green)

def cleanup():

    set_model1_state(0, 0, 0)

    GPIO.cleanup()