import json
from datetime import datetime


def create_heartbeat(intersection_id: int):

    return json.dumps({
        "type": "heartbeat",
        "intersection_id": intersection_id,
        "timestamp": datetime.now().isoformat()
    })


def create_vehicle_count(
    intersection_id: int,
    sensor_id: int,
    count: int
):

    return json.dumps({
        "type": "vehicle_count",
        "intersection_id": intersection_id,
        "sensor_id": sensor_id,
        "count": count,
        "timestamp": datetime.now().isoformat()
    })


def create_speed_violation(
    intersection_id: int,
    sensor_id: int,
    speed: float
):

    return json.dumps({
        "type": "speed_violation",
        "intersection_id": intersection_id,
        "sensor_id": sensor_id,
        "speed": speed,
        "timestamp": datetime.now().isoformat()
    })


def parse_message(message: str):

    return json.loads(message)
