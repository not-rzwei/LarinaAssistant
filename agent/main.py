import sys

from maa.agent.agent_server import AgentServer
from maa.toolkit import Toolkit

import select_wish
import shop_item
import bounty

import threading
import os
import signal


def main():
    Toolkit.init_option("./")

    socket_id = sys.argv[-1]

    def run_server():
        AgentServer.start_up(socket_id)
        AgentServer.join()

    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, terminating immediately...")
        os._exit(0)

    # Register signal handlers BEFORE starting the server thread
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    try:
        # Simple wait for server thread
        while server_thread.is_alive():
            server_thread.join(timeout=0.5)
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received, terminating...")
        os._exit(0)
    except Exception as e:
        print(f"Exception occurred: {e}, terminating...")
        os._exit(1)


if __name__ == "__main__":
    main()
