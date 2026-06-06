"""
Constantes para servidores distribuídos
"""

# GPIO Pins - Controle de Semáforos
# Formato: (cruzamento, bit) -> GPIO
GPIO_TRAFFIC_CONTROL = {
    (1, 0): 17,   # Cruzamento 1, Bit 0
    (1, 1): 18,   # Cruzamento 1, Bit 1
    (1, 2): 23,   # Cruzamento 1, Bit 2
    (2, 0): 24,   # Cruzamento 2, Bit 0
    (2, 1): 8,    # Cruzamento 2, Bit 1
    (2, 2): 7,    # Cruzamento 2, Bit 2
}

# GPIO Pins - Botões de Pedestre (Entradas)
GPIO_PEDESTRIAN_BUTTONS = {
    "1_main": 1,    # Cruzamento 1, Via Principal
    "1_cross": 12,  # Cruzamento 1, Via de Cruzamento
    "2_main": 25,   # Cruzamento 2, Via Principal
    "2_cross": 22,  # Cruzamento 2, Via de Cruzamento
}

# GPIO Pins - Sensores de Velocidade (Entradas)
GPIO_SPEED_SENSORS = {
    1: {"a": 16, "b": 20},   # Sensor 1 (Cruzamento 1)
    2: {"a": 21, "b": 27},   # Sensor 2 (Cruzamento 1)
    3: {"a": 11, "b": 0},    # Sensor 3 (Cruzamento 2)
    4: {"a": 5,  "b": 6},    # Sensor 4 (Cruzamento 2)
}

# Distância entre sensores (em metros)
SENSOR_DISTANCE = 2.5

# Limite de velocidade para registrar infração (km/h)
SPEED_VIOLATION_LIMIT = 60

# Temporização dos semáforos (segundos)
TRAFFIC_TIMING = {
    "main_green_min": 15,
    "main_green_max": 30,
    "main_yellow": 3,
    "all_red": 2,
    "cross_green_min": 5,
    "cross_green_max": 10,
    "cross_yellow": 3,
}

# Modo noturno
NIGHT_MODE_CYCLE_TIME = 1.0  # 1 segundo em cada estado

# Comunicação central
CENTRAL_RECONNECT_INTERVAL = 2  # segundos
HEARTBEAT_INTERVAL = 2  # segundos
VEHICLE_COUNT_REPORT_INTERVAL = 2  # segundos
