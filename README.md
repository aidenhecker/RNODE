# RNODE — a Reticulum LoRa station in a box

> Not the [RNode firmware](https://github.com/markqvist/RNode_Firmware) itself —
> this is a station toolkit *built around* boards running that firmware.

One CLI to run a complete off-grid comms station on a Mac + a LoRa dev board
flashed with [RNode firmware](https://github.com/markqvist/RNode_Firmware):
web chat, radio tuning with an **AI copilot**, and a bidirectional
**Meshtastic↔Reticulum bridge** so your Meshtastic friends aren't left behind.

```
rnode run        # start everything + open the chat in your browser
rnode ai         # "make my link reach further" → it tunes SF/BW/power with you
rnode preset longrange
rnode power 22
rnode device --info
```

## What's inside

| Piece | What it does |
|---|---|
| `cli/rnode` | Station control: daemons up/down, radio params, presets, rnodeconf passthrough, logs, AI copilot |
| `meshtastic-lxmf-bridge/` | Bidirectional Meshtastic↔LXMF bridge — broadcasts **and DMs**, reverse flow with `@name msg` targeting, owner-only auth, 26 tests |
| `claude-peer/` | Minimal LXMF peer pattern: inbox.log + outbox/ files — wire any agent/AI into your mesh |
| `setup/` | Reference Reticulum config (RNodeInterface for a Heltec V4 @ US 915) |

## Requirements

- A board running [RNode firmware](https://unsigned.io/rnode) ≥1.84
  (Heltec V4 supported since 1.84; flash with `rnodeconf --autoinstall`)
- Python 3.12+, [uv](https://github.com/astral-sh/uv), Node 18+ (for MeshChat's frontend)
- [Reticulum](https://reticulum.network) (`pipx install rns`) and
  [reticulum-meshchat](https://github.com/liamcottle/reticulum-meshchat)
  cloned as a sibling directory (or set `RNODE_MESHCHAT_DIR`)

## Install

```bash
git clone <this repo> RNODE && cd RNODE
ln -s "$PWD/cli/rnode" ~/.local/bin/rnode
# bridge setup (optional — needs a second board running Meshtastic):
cd meshtastic-lxmf-bridge && uv venv -p 3.12 .venv && uv pip install -e ".[dev]" -p .venv/bin/python
cp config.example.toml config.toml   # set serial port + your LXMF address
```

## The AI copilot

`rnode ai setup` stores an [OpenRouter](https://openrouter.ai/keys) key
(`~/.config/rnode/openrouter_key`, 0600). Then:

```
$ rnode ai my homie is 4km away and messages arent getting through
```

The copilot sees your live radio params, noise floor, and airtime each turn,
reasons about the link budget, and proposes concrete changes as
`APPLY: preset longrange` / `APPLY: set txpower 22` lines — **you confirm every
change before it touches the radio.** It knows the FCC EIRP rules and that
modulation changes must match on every node in your network.
Model: `anthropic/claude-sonnet-5` by default (`RNODE_AI_MODEL` to override).

## The bridge

Your RNode speaks Reticulum; your friends' radios speak Meshtastic. The bridge
(a second cheap board stays on Meshtastic as the "ear") forwards every mesh
text — including DMs — to your LXMF client, and routes your replies back:
`@shortname message` → Meshtastic DM, plain text → broadcast, `/nodes` → who's
out there. Existing integrations do one-way broadcast only; this does both
directions with per-node targeting.

## License

MIT
