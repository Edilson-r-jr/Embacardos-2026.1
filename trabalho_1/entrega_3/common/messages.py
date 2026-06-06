import json


def create_heartbeat(intersection_id: int):

    return json.dumps({
        "type": "heartbeat",
        "intersection_id": intersection_id
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
        "count": count
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
        "speed": speed
    })


def parse_message(message: str):

    return json.loads(message)