import sys

from maa.agent.agent_server import AgentServer
from maa.toolkit import Toolkit

import recognition

import threading
import os
import signal

def main():
    Toolkit.init_option("./")

    socket_id = sys.argv[-1]

    def run_server():
        AgentServer.start_up(socket_id)
        AgentServer.join()

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True  # Make sure thread does not block exit
    server_thread.start()

    def force_exit(signum=None, frame=None):
        print("Forcefully killing process...")
        os._exit(1)

    # Register signal handlers for utmost priority exit
    signal.signal(signal.SIGINT, force_exit)
    signal.signal(signal.SIGTERM, force_exit)

    try:
        while True:
            server_thread.join(timeout=0.5)
            if not server_thread.is_alive():
                break
    except Exception as e:
        # On any exception, force exit
        print(f"Exception occurred: {e}, forcefully killing process...")
        os._exit(1)
    finally:
        # In case shutdown is called from other exceptions, still force kill if needed
        if server_thread.is_alive():
            os._exit(1)

if __name__ == "__main__":
    main()
