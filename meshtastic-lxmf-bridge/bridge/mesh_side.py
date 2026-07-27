import logging
import threading
import time

from pubsub import pub

from .nodecache import NodeCache

log = logging.getLogger("bridge.mesh")

BROADCAST_IDS = ("^all", "!ffffffff")


class MeshtasticLink:
    """Owns the connection to the local Meshtastic node (serial or TCP).

    on_text(from_id: str, label: str, text: str, is_dm: bool) is called for
    every inbound text message. Reconnects with capped exponential backoff.
    """

    def __init__(self, config, on_text, interface_factory=None):
        self.config = config
        self.on_text = on_text
        self.nodes = NodeCache()
        self.interface = None
        self.my_id = None
        self._factory = interface_factory or self._default_factory
        self._stop = threading.Event()
        self._thread = None

    # -- connection ---------------------------------------------------------

    def _default_factory(self):
        if self.config.connection == "tcp":
            from meshtastic.tcp_interface import TCPInterface
            return TCPInterface(hostname=self.config.host)
        from meshtastic.serial_interface import SerialInterface
        return SerialInterface(devPath=self.config.port)

    def start(self):
        pub.subscribe(self._on_receive, "meshtastic.receive")
        pub.subscribe(self._on_connection_lost, "meshtastic.connection.lost")
        self._thread = threading.Thread(target=self._run, daemon=True, name="mesh-link")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self.interface is not None:
            try:
                self.interface.close()
            except Exception:
                pass

    def _run(self):
        backoff = 2
        while not self._stop.is_set():
            if self.interface is None:
                try:
                    self.interface = self._factory()
                    self._learn_self_and_nodes()
                    backoff = 2
                    log.info("connected to Meshtastic node %s", self.my_id)
                except Exception as e:
                    log.warning("Meshtastic connect failed (%s), retry in %ss", e, backoff)
                    self.interface = None
                    self._stop.wait(backoff)
                    backoff = min(backoff * 2, 60)
            else:
                self._stop.wait(1)

    def _on_connection_lost(self, interface=None):
        log.warning("Meshtastic connection lost")
        self.interface = None

    def _learn_self_and_nodes(self):
        info = getattr(self.interface, "myInfo", None)
        nodes = getattr(self.interface, "nodes", None) or {}
        for node_id, node in nodes.items():
            user = node.get("user", {}) if isinstance(node, dict) else {}
            self.nodes.update(node_id, user.get("shortName"), user.get("longName"))
        if info is not None:
            my_num = getattr(info, "my_node_num", None)
            for node_id, node in nodes.items():
                if isinstance(node, dict) and node.get("num") == my_num:
                    self.my_id = node_id
                    break

    # -- inbound ------------------------------------------------------------

    def _on_receive(self, packet, interface=None):
        try:
            decoded = packet.get("decoded", {})
            portnum = decoded.get("portnum")
            from_id = packet.get("fromId")

            if portnum == "NODEINFO_APP":
                user = decoded.get("user", {})
                self.nodes.update(from_id, user.get("shortName"), user.get("longName"))
                return

            if portnum != "TEXT_MESSAGE_APP":
                return
            if from_id and from_id == self.my_id:
                return  # our own transmission echoed back

            text = decoded.get("text", "")
            to_id = packet.get("toId")
            is_dm = to_id not in BROADCAST_IDS and to_id is not None
            self.on_text(from_id, self.nodes.label(from_id), text, is_dm)
        except Exception:
            log.exception("error handling inbound Meshtastic packet")

    # -- outbound -----------------------------------------------------------

    def send_broadcast(self, text: str):
        self._send(text, None)

    def send_dm(self, dest_id: str, text: str):
        self._send(text, dest_id)

    def _send(self, text: str, dest_id: str | None):
        if self.interface is None:
            raise ConnectionError("Meshtastic link is down")
        if dest_id is None:
            self.interface.sendText(text)
        else:
            self.interface.sendText(text, destinationId=dest_id)
