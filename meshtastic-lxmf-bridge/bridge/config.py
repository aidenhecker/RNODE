import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MeshtasticConfig:
    connection: str = "serial"          # "serial" | "tcp"
    port: str = ""                      # serial device path, e.g. /dev/cu.usbmodem2101
    host: str = "127.0.0.1"             # for tcp connections (meshtasticd / WiFi node)


@dataclass
class LXMFConfig:
    owner_address: str = ""             # LXMF address (hex) allowed to command the bridge
    display_name: str = "MTX Bridge"
    announce_interval: int = 1800       # seconds between LXMF announces
    storage_dir: str = "storage"


@dataclass
class BridgeConfig:
    meshtastic: MeshtasticConfig = field(default_factory=MeshtasticConfig)
    lxmf: LXMFConfig = field(default_factory=LXMFConfig)

    @classmethod
    def load(cls, path: str | Path) -> "BridgeConfig":
        with open(path, "rb") as f:
            raw = tomllib.load(f)
        cfg = cls(
            meshtastic=MeshtasticConfig(**raw.get("meshtastic", {})),
            lxmf=LXMFConfig(**raw.get("lxmf", {})),
        )
        if cfg.meshtastic.connection not in ("serial", "tcp"):
            raise ValueError(f"invalid meshtastic.connection: {cfg.meshtastic.connection}")
        if cfg.meshtastic.connection == "serial" and not cfg.meshtastic.port:
            raise ValueError("meshtastic.port required for serial connection")
        if not cfg.lxmf.owner_address:
            raise ValueError("lxmf.owner_address is required (your MeshChat/Sideband address hash)")
        bytes.fromhex(cfg.lxmf.owner_address)  # validate hex early
        return cfg
