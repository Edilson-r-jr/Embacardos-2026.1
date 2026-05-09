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

# Modelo 2
GPIO.setup(M2_BIT0, GPIO.OUT)
GPIO.setup(M2_BIT1, GPIO.OUT)
GPIO.setup(M2_BIT2, GPIO.OUT)

# Botões
GPIO.setup(M2_BUTTON_MAIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(M2_BUTTON_CROSS, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# =========================
# FUNÇÕES
# =========================

def set_model1_state(red, yellow, green):

    GPIO.output(M1_RED_LED, red)
    GPIO.output(M1_YELLOW_LED, yellow)
    GPIO.output(M1_GREEN_LED, green)

def set_model2_state(code):

    bit0 = code & 1
    bit1 = (code >> 1) & 1
    bit2 = (code >> 2) & 1

    GPIO.output(M2_BIT0, bit0)
    GPIO.output(M2_BIT1, bit1)
    GPIO.output(M2_BIT2, bit2)

def cleanup():

    set_model1_state(0, 0, 0)

    GPIO.cleanup()