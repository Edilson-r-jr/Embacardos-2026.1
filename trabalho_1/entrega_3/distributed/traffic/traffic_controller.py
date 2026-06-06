from .traffic_states import TrafficState


class TrafficController:

    DURATIONS = {
        TrafficState.MAIN_GREEN: 15,
        TrafficState.MAIN_YELLOW: 3,
        TrafficState.ALL_RED_1: 2,
        TrafficState.CROSS_GREEN: 5,
        TrafficState.CROSS_YELLOW: 3,
        TrafficState.ALL_RED_2: 2,
    }

    @classmethod
    def get_duration(cls, state):
        return cls.DURATIONS[state]

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