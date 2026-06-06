import json
import sys
import time
import os


def is_raspberry_pi():
    """Detecta se está rodando em uma Raspberry Pi"""
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read()
            return "Raspberry Pi" in model
    except:
        # Se não conseguir ler, assume que não é RPi
        return False


from distributed.network.tcp_client import TCPClient
from distributed.traffic.traffic_state_machine import TrafficStateMachine
from distributed.gpio.traffic_light_controller import TrafficLightController
from distributed.gpio.sensor_reader import (
    SpeedSensorReader, PedestrianButtonReader
)


def load_config(path):
    with open(path, "r") as file:
        return json.load(file)


def main():

    if len(sys.argv) < 2:
        print("Uso: python -m distributed.main config.json [--mock]")
        return

    config = load_config(sys.argv[1])
    
    # Detecta modo: --mock explícito, ou auto-detecta com base em RPi
    if "--mock" in sys.argv:
        use_mock = True
        print("[DIST] Modo MOCK forçado via --mock")
    else:
        use_mock = not is_raspberry_pi()
        mode_str = "MOCK (não é RPi)" if use_mock else "HARDWARE (RPi detectada)"
        print(f"[DIST] Modo: {mode_str}")
    
    intersection_id = config["intersection_id"]
    
    print(f"[DIST {intersection_id}] Inicializando...")
    
    # Inicializa máquina de estados de tráfego
    traffic = TrafficStateMachine(intersection_id)
    
    # Inicializa cliente TCP
    client = TCPClient(
        host=config["central_host"],
        port=config["central_port"],
        intersection_id=intersection_id,
        traffic_state_machine=traffic
    )
    
    # Inicializa controlador de semáforos (GPIO)
    try:
        traffic_lights = TrafficLightController(
            intersection_id,
            use_mock=use_mock
        )
        traffic.set_traffic_light_controller(traffic_lights)
    except Exception as e:
        print(f"[DIST {intersection_id}] Erro ao inicializar GPIO de semáforos: {e}")
        if not use_mock:
            print("[DIST] Executando em modo MOCK como fallback")
            use_mock = True
            traffic_lights = TrafficLightController(intersection_id, use_mock=True)
            traffic.set_traffic_light_controller(traffic_lights)
    
    # Inicializa sensores de velocidade
    sensors = {}
    try:
        # Sensores por cruzamento: 1,2 para cruzamento 1 e 3,4 para cruzamento 2
        if intersection_id == 1:
            sensor_ids = [1, 2]
        else:
            sensor_ids = [3, 4]
        
        for sensor_id in sensor_ids:
            sensors[sensor_id] = SpeedSensorReader(sensor_id, use_mock=use_mock)
        
        # Passa sensores para o cliente
        client.set_speed_sensors(sensors)
        print(f"[DIST {intersection_id}] Sensores de velocidade inicializados")
    except Exception as e:
        print(f"[DIST {intersection_id}] Erro ao inicializar sensores: {e}")
    
    # Inicializa botões de pedestre
    try:
        ped_buttons = PedestrianButtonReader(intersection_id, use_mock=use_mock)
        
        # Registra callbacks
        def on_main_button():
            print(f"[DIST {intersection_id}] Botão principal acionado")
            traffic.pedestrian_button_pressed("main")
        
        def on_cross_button():
            print(f"[DIST {intersection_id}] Botão cruzamento acionado")
            traffic.pedestrian_button_pressed("cross")
        
        ped_buttons.add_callback("main", on_main_button)
        ped_buttons.add_callback("cross", on_cross_button)
        ped_buttons.start_polling()
        
        print(f"[DIST {intersection_id}] Botões de pedestre inicializados")
    except Exception as e:
        print(f"[DIST {intersection_id}] Erro ao inicializar botões: {e}")
    
    # Inicia threads
    traffic.start()
    client.start()
    
    print(f"[DIST {intersection_id}] Sistema iniciado com sucesso")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[DIST {intersection_id}] Desligando...")
        client.stop()
        try:
            ped_buttons.stop_polling()
        except:
            pass
        try:
            traffic_lights.cleanup()
        except:
            pass


if __name__ == "__main__":
    main()


