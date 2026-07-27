import logging
import threading
import time
from pathlib import Path

log = logging.getLogger("bridge.lxmf")


class LXMFLink:
    """Bridge identity on the Reticulum side.

    Delivers inbound Meshtastic traffic to the owner's LXMF address and
    surfaces owner replies via on_message(text). Only the configured owner
    may command the bridge — everything else is logged and dropped.
    """

    def __init__(self, config, on_message):
        self.config = config
        self.on_message = on_message
        self.router = None
        self.destination = None
        self.owner_hash = bytes.fromhex(config.owner_address)
        self._announce_thread = None
        self._stop = threading.Event()

    def start(self):
        import RNS
        import LXMF

        self._rns = RNS
        self._lxmf = LXMF

        storage = Path(self.config.storage_dir)
        storage.mkdir(parents=True, exist_ok=True)
        identity_path = storage / "bridge_identity"

        RNS.Reticulum()  # attaches to the shared instance if one is running

        if identity_path.exists():
            identity = RNS.Identity.from_file(str(identity_path))
        else:
            identity = RNS.Identity()
            identity.to_file(str(identity_path))

        self.router = LXMF.LXMRouter(identity=identity, storagepath=str(storage / "lxmf"))
        self.router.register_delivery_callback(self._on_lxmf_delivery)
        self.destination = self.router.register_delivery_identity(
            identity, display_name=self.config.display_name
        )
        log.info("bridge LXMF address: %s", RNS.prettyhexrep(self.destination.hash))

        self._announce_thread = threading.Thread(
            target=self._announce_loop, daemon=True, name="lxmf-announce"
        )
        self._announce_thread.start()

    def stop(self):
        self._stop.set()

    def _announce_loop(self):
        while not self._stop.is_set():
            try:
                self.router.announce(self.destination.hash)
                log.debug("announced bridge destination")
            except Exception:
                log.exception("announce failed")
            self._stop.wait(self.config.announce_interval)

    # -- inbound (owner -> bridge -> mesh) -----------------------------------

    def _on_lxmf_delivery(self, message):
        try:
            source = message.source_hash
            if source != self.owner_hash:
                log.warning(
                    "dropping LXMF message from non-owner %s",
                    self._rns.prettyhexrep(source),
                )
                return
            text = message.content.decode("utf-8", errors="replace").strip()
            if text:
                self.on_message(text)
        except Exception:
            log.exception("error handling inbound LXMF message")

    # -- outbound (mesh -> bridge -> owner) -----------------------------------

    def send_to_owner(self, text: str, title: str = ""):
        RNS, LXMF = self._rns, self._lxmf

        if not RNS.Transport.has_path(self.owner_hash):
            RNS.Transport.request_path(self.owner_hash)
            deadline = time.time() + 15
            while not RNS.Transport.has_path(self.owner_hash) and time.time() < deadline:
                time.sleep(0.2)

        owner_identity = RNS.Identity.recall(self.owner_hash)
        if owner_identity is None:
            log.error("owner identity unknown — has your LXMF client announced yet?")
            return False

        owner_dest = RNS.Destination(
            owner_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )
        lm = LXMF.LXMessage(
            owner_dest,
            self.destination,
            text.encode("utf-8"),
            title.encode("utf-8"),
            desired_method=LXMF.LXMessage.DIRECT,
        )
        lm.try_propagation_on_fail = True
        self.router.handle_outbound(lm)
        return True
