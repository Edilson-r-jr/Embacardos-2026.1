import RPi.GPIO as GPIO
import time

# =========================
# PINOS
# =========================

GREEN_LED = 17
YELLOW_LED = 18
RED_LED = 23

BUTTON_MAIN = 1
BUTTON_CROSS = 12

# =========================
# CONFIGURAÇÃO GPIO
# =========================

GPIO.setmode(GPIO.BCM)

GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(YELLOW_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)

GPIO.setup(BUTTON_MAIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(BUTTON_CROSS, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# =========================
# VARIÁVEIS
# =========================

pedestrian_request = False

# =========================
# FUNÇÕES
# =========================

def set_state(red, yellow, green):
    GPIO.output(RED_LED, red)
    GPIO.output(YELLOW_LED, yellow)
    GPIO.output(GREEN_LED, green)

def button_callback(channel):
    global pedestrian_request

    pedestrian_request = True

    print(f"Botão pressionado no GPIO {channel}")

# =========================
# INTERRUPÇÕES DOS BOTÕES
# =========================

GPIO.add_event_detect(
    BUTTON_MAIN,
    GPIO.RISING,
    callback=button_callback,
    bouncetime=200
)

GPIO.add_event_detect(
    BUTTON_CROSS,
    GPIO.RISING,
    callback=button_callback,
    bouncetime=200
)

# =========================
# LOOP PRINCIPAL
# =========================

try:

    while True:

        # =====================
        # VERDE
        # =====================

        pedestrian_request = False

        set_state(0, 0, 1)

        print("VERDE")

        start_time = time.time()

        while True:

            elapsed = time.time() - start_time

            # terminou tempo máximo
            if elapsed >= 10:
                break

            # botão pressionado após tempo mínimo
            if pedestrian_request and elapsed >= 5:
                print("Mudança antecipada por pedestre")
                break

            time.sleep(0.1)

        # =====================
        # AMARELO
        # =====================

        set_state(0, 1, 0)

        print("AMARELO")

        time.sleep(2)

        # =====================
        # VERMELHO
        # =====================

        set_state(1, 0, 0)

        print("VERMELHO")

        time.sleep(10)

except KeyboardInterrupt:

    print("\nEncerrando...")

finally:

    GPIO.cleanup()