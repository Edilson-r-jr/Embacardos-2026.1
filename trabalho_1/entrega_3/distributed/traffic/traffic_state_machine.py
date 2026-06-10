import threading
import time

from .traffic_controller import TrafficController
from .traffic_states import TrafficState


class TrafficStateMachine(threading.Thread):

    def __init__(self, intersection_id):
        super().__init__(daemon=True)

        self.intersection_id = intersection_id
        self.current_state = TrafficState.MAIN_GREEN
        
        # Modo noturno: alterna entre amarelo (0) e vermelho (4)
        self.night_mode = False
        self.night_mode_toggle = False
        self.night_mode_last_toggle = 0
        
        # Modo de emergência
        self.emergency_active = False
        self.emergency_signal_group = 0  # 1=main, 2=cross
        
        # Controlador de semáforos (GPIO)
        self.traffic_light_controller = None
        
        # Botões de pedestre
        self.pedestrian_requests = {"main": False, "cross": False}

        # Controle manual: None = sem override, int = código de estado forçado
        self.manual_override = None

        self.lock = threading.Lock()

    def set_traffic_light_controller(self, controller):
        """Define o controlador de semáforos (GPIO)"""
        self.traffic_light_controller = controller
    
    def pedestrian_button_pressed(self, button_type):
        """Chamado quando um botão de pedestre é pressionado"""
        with self.lock:
            self.pedestrian_requests[button_type] = True
            print(f"[DIST {self.intersection_id}] Pedestre solicitou passagem: {button_type}")

    def run(self):
        while True:
            with self.lock:
                manual = self.manual_override
            if manual is not None:
                self.handle_manual_override()
            elif self.night_mode:
                self.handle_night_mode()
            elif self.emergency_active:
                self.handle_emergency_mode()
            else:
                self.handle_normal_mode()

    def handle_night_mode(self):
        """Modo noturno: alterna entre amarelo e vermelho a cada 1 segundo"""
        with self.lock:
            current_time = time.time()
            
            # Alterna a cada 1 segundo
            if current_time - self.night_mode_last_toggle >= 1.0:
                self.night_mode_toggle = not self.night_mode_toggle
                self.night_mode_last_toggle = current_time
            
            # Estado 0: amarelo | Estado 4: vermelho (apagado)
            state_code = 0 if self.night_mode_toggle else 4
        
        print(f"[DIST {self.intersection_id}] NIGHT_MODE (código={state_code})")
        
        # Escreve no GPIO
        if self.traffic_light_controller:
            self.traffic_light_controller.set_state(state_code)
        
        time.sleep(0.5)

    def handle_emergency_mode(self):
        """Modo de emergência: abre via de emergência"""
        with self.lock:
            signal_group = self.emergency_signal_group
        
        # signal_group: 1=abrir main, 2=abrir cross
        if signal_group == 1:
            # Abre via principal (estado 1: main_green, cross_red)
            state = TrafficState.MAIN_GREEN
            state_code = 1
            print(f"[DIST {self.intersection_id}] EMERGENCY_MAIN_GREEN")
        else:
            # Abre via auxiliar (estado 5: main_red, cross_green)
            state = TrafficState.CROSS_GREEN
            state_code = 5
            print(f"[DIST {self.intersection_id}] EMERGENCY_CROSS_GREEN")
        
        # Escreve no GPIO
        if self.traffic_light_controller:
            self.traffic_light_controller.set_state(state_code)
        
        time.sleep(1)

    def handle_normal_mode(self):
        """Modo normal: máquina de estados com suporte a pedestre e interrupção de modo."""
        with self.lock:
            current_state = self.current_state
            ped_key = TrafficController.get_pedestrian_key(current_state)
            # Descarta request acumulado de ciclos anteriores ao entrar no estado
            if ped_key:
                self.pedestrian_requests[ped_key] = False

        min_dur = TrafficController.get_min_duration(current_state)
        max_dur = TrafficController.get_max_duration(current_state)
        state_code = self._state_to_code(current_state)

        print(
            f"[DIST {self.intersection_id}] "
            f"{current_state.name} ({min_dur}–{max_dur}s) - Código: {state_code}"
        )

        if self.traffic_light_controller:
            self.traffic_light_controller.set_state(state_code)

        start = time.time()
        while True:
            # Prioridade máxima: mudança de modo — retorna sem avançar o estado
            with self.lock:
                if self.night_mode or self.emergency_active:
                    return

            elapsed = time.time() - start

            # Tempo máximo sempre avança o estado
            if elapsed >= max_dur:
                break

            # Após o mínimo, verifica botão de pedestre (apenas fases verdes)
            if elapsed >= min_dur:
                if ped_key:
                    with self.lock:
                        if self.pedestrian_requests.get(ped_key, False):
                            self.pedestrian_requests[ped_key] = False
                            print(
                                f"[DIST {self.intersection_id}] "
                                f"Pedestre '{ped_key}': antecipando mudança "
                                f"({elapsed:.1f}s/{min_dur}s mínimo)"
                            )
                            break
                else:
                    # Estados de duração fixa (amarelo, vermelho total): avança ao atingir mínimo
                    break

            time.sleep(0.1)

        with self.lock:
            self.current_state = TrafficController.next_state(current_state)
    
    def _state_to_code(self, state):
        """Converte estado da máquina para código de semáforo de 3 bits"""
        # Mapeamento de estados para códigos de semáforo
        state_codes = {
            TrafficState.MAIN_GREEN: 1,      # Via principal verde
            TrafficState.MAIN_YELLOW: 2,     # Via principal amarelo
            TrafficState.ALL_RED_1: 4,       # Vermelho total
            TrafficState.CROSS_GREEN: 5,     # Via cruzamento verde
            TrafficState.CROSS_YELLOW: 6,    # Via cruzamento amarelo
            TrafficState.ALL_RED_2: 4,       # Vermelho total
        }
        return state_codes.get(state, 0)

    def handle_manual_override(self):
        with self.lock:
            code = self.manual_override
        if self.traffic_light_controller:
            self.traffic_light_controller.set_state(code)
        time.sleep(0.5)

    def set_manual_override(self, state_code):
        """Força um estado fixo no semáforo. state_code=None retoma o fluxo normal."""
        with self.lock:
            self.manual_override = state_code
            if state_code is None:
                self.current_state = TrafficState.MAIN_GREEN
                self.emergency_active = False
                self.night_mode = False

    def set_night_mode(self, enabled):
        """Ativa/desativa modo noturno"""
        with self.lock:
            self.night_mode = enabled
            if enabled:
                self.night_mode_toggle = False
                self.night_mode_last_toggle = time.time()

    def set_emergency(self, active, signal_group=0):
        """Ativa/desativa modo de emergência"""
        with self.lock:
            self.emergency_active = active
            self.emergency_signal_group = signal_group
            if not active:
                # Volta ao estado inicial
                self.current_state = TrafficState.MAIN_GREEN
