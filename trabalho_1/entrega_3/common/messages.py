import json


def create_heartbeat(intersection_id: int):

    return json.dumps({
        "type": "heartbeat",
        "intersection_id": intersection_id
    })


def parse_message(message: str):

    return json.loads(message)