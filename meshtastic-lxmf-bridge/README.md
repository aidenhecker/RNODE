# meshtastic-lxmf-bridge

Bidirectional text bridge between a **Meshtastic** mesh and **Reticulum LXMF**.
Closes the two gaps existing integrations leave open: **direct messages** and
the **reverse (Reticulum → Meshtastic) flow**.

```
[homie's Meshtastic radio] ~RF~ [local Meshtastic node] --USB/TCP--> bridge <--LXMF--> [MeshChat / Sideband]
```

## What it does

- Every text heard on the mesh (broadcast **and** DMs to the bridge node) is
  delivered to your LXMF address, labelled `[shortName]`, DMs marked `→ you`.
- Replies from your LXMF client:
  - `@<shortName|longName|!nodeid> message` → Meshtastic **DM**
  - plain text → **channel-0 broadcast**
  - `/nodes` → node directory the bridge has heard
- Only the configured `owner_address` may command the bridge; other LXMF
  senders are dropped and logged.
- Both links reconnect with capped exponential backoff.

## Requirements

- A **second radio running Meshtastic** attached via USB (`connection = "serial"`)
  or reachable over WiFi/TCP (`connection = "tcp"`, port 4403) — the bridge's
  ear on the mesh. (One radio can't speak both protocols at once.)
- A running Reticulum instance (e.g. MeshChat or rnsd with a shared instance);
  the bridge attaches to it.

## Setup

```bash
uv venv -p 3.12 .venv && uv pip install -e . -p .venv/bin/python
cp config.example.toml config.toml   # edit: serial port + your LXMF address
.venv/bin/python -m bridge -c config.toml
```

Your LXMF address is shown in MeshChat (About/Identity) or Sideband. First
message delivery requires your client to have announced — send the bridge a
message first, or wait for its announce and message it once.

## Tests

```bash
uv pip install -e ".[dev]" -p .venv/bin/python
.venv/bin/python -m pytest
```

## Design notes

- `bridge/mesh_side.py` — Meshtastic connection, node cache from NODEINFO,
  inbound text dispatch, sendText out.
- `bridge/lxmf_side.py` — persistent bridge identity, LXMF router, owner
  auth, delivery + announce loop.
- `bridge/core.py` — the actual bridging policy (`@target` parsing, labels).
- v2 idea: per-Meshtastic-node virtual LXMF identities so each mesh user
  appears as a distinct peer in your client.
