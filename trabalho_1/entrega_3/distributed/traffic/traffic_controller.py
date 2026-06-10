from .traffic_states import TrafficState


class TrafficController:

    _MIN = {
        TrafficState.MAIN_GREEN:   15,
        TrafficState.MAIN_YELLOW:   3,
        TrafficState.ALL_RED_1:     2,
        TrafficState.CROSS_GREEN:   5,
        TrafficState.CROSS_YELLOW:  3,
        TrafficState.ALL_RED_2:     2,
    }

    _MAX = {
        TrafficState.MAIN_GREEN:   30,
        TrafficState.MAIN_YELLOW:   3,
        TrafficState.ALL_RED_1:     2,
        TrafficState.CROSS_GREEN:  10,
        TrafficState.CROSS_YELLOW:  3,
        TrafficState.ALL_RED_2:     2,
    }

    # Botão de pedestre que pode antecipar cada fase verde
    _PEDESTRIAN_KEY = {
        TrafficState.MAIN_GREEN:  "main",
        TrafficState.CROSS_GREEN: "cross",
    }

    @classmethod
    def get_duration(cls, state):
        return cls._MIN[state]

    @classmethod
    def get_min_duration(cls, state):
        return cls._MIN[state]

    @classmethod
    def get_max_duration(cls, state):
        return cls._MAX[state]

    @classmethod
    def get_pedestrian_key(cls, state):
        """Retorna qual flag de pedestre pode antecipar este estado, ou None."""
        return cls._PEDESTRIAN_KEY.get(state)

    @classmethod
    def next_state(cls, state):

        if state == TrafficState.MAIN_GREEN:
            return TrafficState.MAIN_YELLOW

        if state == TrafficState.MAIN_YELLOW:
            return TrafficState.ALL_RED_1

        if state == TrafficState.ALL_RED_1:
            return TrafficState.CROSS_GREEN

        if state == TrafficState.CROSS_GREEN:
            return TrafficState.CROSS_YELLOW

        if state == TrafficState.CROSS_YELLOW:
            return TrafficState.ALL_RED_2

        return TrafficState.MAIN_GREEN
