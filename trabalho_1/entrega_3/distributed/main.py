import json
import sys

from distributed.network.tcp_client import (
    TCPClient
)


def load_config(path):

    with open(path, "r") as file:

        return json.load(file)


def main():

    if len(sys.argv) != 2:

        print(
            "Uso: python main.py "
            "config.json"
        )

        return

    config = load_config(
        sys.argv[1]
    )

    client = TCPClient(
        host=config["central_host"],
        port=config["central_port"],
        intersection_id=config[
            "intersection_id"
        ]
    )

    client.connect()

    client.send_heartbeat()


if __name__ == "__main__":

    main()