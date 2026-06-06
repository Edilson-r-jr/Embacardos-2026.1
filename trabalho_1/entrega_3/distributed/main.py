import json
import sys
import time

from distributed.network.tcp_client import (
    TCPClient
)

from distributed.traffic.traffic_state_machine import (
    TrafficStateMachine
)


def load_config(path):

    with open(path, "r") as file:
        return json.load(file)


def main():

    if len(sys.argv) != 2:

        print(
            "Uso: python -m distributed.main config.json"
        )

        return

    config = load_config(
        sys.argv[1]
    )

    client = TCPClient(
        host=config["central_host"],
        port=config["central_port"],
        intersection_id=config["intersection_id"]
    )

    traffic = TrafficStateMachine(
        config["intersection_id"]
    )

    client.start()

    time.sleep(2)

    traffic.start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()