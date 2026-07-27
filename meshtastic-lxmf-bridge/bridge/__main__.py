import argparse
import logging
import signal
import sys
import threading

from .config import BridgeConfig
from .core import Bridge
from .lxmf_side import LXMFLink
from .mesh_side import MeshtasticLink


def main():
    parser = argparse.ArgumentParser(description="Meshtastic <-> LXMF bridge")
    parser.add_argument("-c", "--config", default="config.toml", help="path to config.toml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    config = BridgeConfig.load(args.config)

    bridge_holder: dict = {}
    mesh = MeshtasticLink(config.meshtastic,
                          on_text=lambda *a: bridge_holder["b"].on_mesh_text(*a))
    lxmf = LXMFLink(config.lxmf,
                    on_message=lambda t: bridge_holder["b"].on_lxmf_text(t))
    bridge_holder["b"] = Bridge(mesh, lxmf)

    lxmf.start()
    mesh.start()

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    logging.getLogger("bridge").info("bridge running — ctrl-c to stop")
    stop.wait()

    mesh.stop()
    lxmf.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
