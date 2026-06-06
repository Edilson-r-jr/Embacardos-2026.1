import threading
import time

from central.network.tcp_server import (
    TCPServer
)

from central.state.state_manager import (
    StateManager
)


def dashboard_loop(state_manager):

    while True:

        print("\n" * 3)

        print("=" * 60)

        snapshot = (
            state_manager.get_snapshot()
        )

        for intersection in (
            snapshot.values()
        ):

            print()

            print(
                f"Cruzamento "
                f"{intersection.intersection_id}"
            )

            status = (
                "ONLINE"
                if intersection.is_online()
                else "OFFLINE"
            )

            print(
                f"Status: {status}"
            )

            heartbeat = (
                intersection
                .seconds_since_heartbeat()
            )

            if heartbeat is None:

                print(
                    "Heartbeat: nunca"
                )

            else:

                print(
                    f"Heartbeat: {heartbeat}s"
                )

            print(
                f"Sensor 1: "
                f"{intersection.vehicle_count[1]}"
            )

            print(
                f"Sensor 2: "
                f"{intersection.vehicle_count[2]}"
            )

            print(
                f"Infrações: "
                f"{intersection.speed_violations}"
            )

        print()
        print("=" * 60)

        time.sleep(2)


def main():

    state_manager = StateManager()

    server = TCPServer(
        state_manager
    )

    threading.Thread(
        target=server.start,
        daemon=True
    ).start()

    dashboard_loop(
        state_manager
    )


if __name__ == "__main__":

    main()