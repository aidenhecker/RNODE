import threading


class NodeCache:
    """Meshtastic node directory: !nodeid <-> short/long names, thread-safe."""

    def __init__(self):
        self._lock = threading.Lock()
        self._nodes: dict[str, dict] = {}  # "!hexid" -> {"short": str, "long": str}

    def update(self, node_id: str, short_name: str | None, long_name: str | None):
        if not node_id:
            return
        with self._lock:
            entry = self._nodes.setdefault(node_id, {"short": "", "long": ""})
            if short_name:
                entry["short"] = short_name
            if long_name:
                entry["long"] = long_name

    def label(self, node_id: str) -> str:
        with self._lock:
            entry = self._nodes.get(node_id)
        if entry and entry["short"]:
            return entry["short"]
        if entry and entry["long"]:
            return entry["long"]
        return node_id or "?"

    def resolve(self, target: str) -> str | None:
        """Resolve '@target' (shortName, longName or !nodeid) to a !nodeid."""
        if target.startswith("!"):
            return target
        t = target.lower()
        with self._lock:
            for node_id, entry in self._nodes.items():
                if entry["short"].lower() == t or entry["long"].lower() == t:
                    return node_id
        return None

    def all(self) -> dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._nodes.items()}
