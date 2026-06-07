"""
Constantes do sistema
"""

# Mapeamento de câmeras LPR por sensor
# sensor_id -> camera_modbus_address
SENSOR_TO_CAMERA = {
    1: 0x11,  # Sensor 1 (Cruzamento 1) -> Câmera 1
    2: 0x12,  # Sensor 2 (Cruzamento 1) -> Câmera 2
    3: 0x13,  # Sensor 3 (Cruzamento 2) -> Câmera 3
    4: 0x14   # Sensor 4 (Cruzamento 2) -> Câmera 4
}

# Limite de velocidade em km/h para registrar infração
SPEED_VIOLATION_LIMIT = 60

# Valor da multa por infração (em reais)
FINE_VALUE = 293.47

# Porta UART/RS485
UART_PORT = "/dev/serial0"

# Estados de semáforo
TRAFFIC_STATES = {
    0: {"main": "yellow", "cross": "yellow", "ped_main": "off", "ped_cross": "off"},
    1: {"main": "green", "cross": "red", "ped_main": "red", "ped_cross": "green"},
    2: {"main": "yellow", "cross": "red", "ped_main": "red", "ped_cross": "red"},
    3: {"main": "yellow", "cross": "red", "ped_main": "red", "ped_cross": "off"},
    4: {"main": "red", "cross": "red", "ped_main": "red", "ped_cross": "red"},
    5: {"main": "red", "cross": "green", "ped_main": "green", "ped_cross": "red"},
    6: {"main": "red", "cross": "yellow", "ped_main": "red", "ped_cross": "red"},
    7: {"main": "red", "cross": "yellow", "ped_main": "off", "ped_cross": "red"},
}

# Modo noturno: alterna entre estado 0 (amarelo) e 4 (vermelho)
NIGHT_MODE_CYCLE_TIME = 1.0  # 1 segundo em cada estado


MATRICULA = bytes([0,2,4,7,9,3])