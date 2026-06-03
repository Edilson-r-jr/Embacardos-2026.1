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

        print("=" * 50)

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
                if intersection.connected
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
                    "Último heartbeat: nunca"
                )

            else:

                print(
                    f"Último heartbeat: "
                    f"{heartbeat}s"
                )

        print()

        print("=" * 50)

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