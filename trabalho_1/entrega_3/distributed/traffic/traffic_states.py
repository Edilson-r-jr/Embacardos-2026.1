from enum import Enum


class TrafficState(Enum):
    MAIN_GREEN = 1
    MAIN_YELLOW = 2
    ALL_RED_1 = 3
    CROSS_GREEN = 4
    CROSS_YELLOW = 5
    ALL_RED_2 = 6