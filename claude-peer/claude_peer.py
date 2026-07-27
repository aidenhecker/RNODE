"""Claude's LXMF peer — lets the user chat with Claude from MeshChat.

Inbound messages append to inbox.log (JSON lines).
Files dropped into outbox/ are sent to the owner and deleted.
"""
import json
import os
import sys
import time
from pathlib import Path

import RNS
import LXMF

BASE = Path(__file__).parent
STORAGE = BASE / "storage"
OUTBOX = BASE / "outbox"
INBOX_LOG = BASE / "inbox.log"

_owner = os.environ.get("RNODE_OWNER_LXMF", "")
if not _owner and (BASE / "owner.txt").exists():
    _owner = (BASE / "owner.txt").read_text().strip()
if not _owner:
    sys.exit("no owner set — put your LXMF address hash in owner.txt or RNODE_OWNER_LXMF")
OWNER = bytes.fromhex(_owner)

STORAGE.mkdir(exist_ok=True)
OUTBOX.mkdir(exist_ok=True)

RNS.Reticulum()

id_path = STORAGE / "identity"
if id_path.exists():
    identity = RNS.Identity.from_file(str(id_path))
else:
    identity = RNS.Identity()
    identity.to_file(str(id_path))

router = LXMF.LXMRouter(identity=identity, storagepath=str(STORAGE / "lxmf"))


def on_delivery(message):
    entry = {
        "time": time.strftime("%H:%M:%S"),
        "from": message.source_hash.hex(),
        "title": message.title.decode("utf-8", errors="replace"),
        "content": message.content.decode("utf-8", errors="replace"),
    }
    with open(INBOX_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


router.register_delivery_callback(on_delivery)
dest = router.register_delivery_identity(identity, display_name="Claude")
print("claude peer address:", RNS.prettyhexrep(dest.hash), flush=True)
router.announce(dest.hash)


def send_to_owner(text: str, title: str = ""):
    if not RNS.Transport.has_path(OWNER):
        RNS.Transport.request_path(OWNER)
        deadline = time.time() + 15
        while not RNS.Transport.has_path(OWNER) and time.time() < deadline:
            time.sleep(0.2)
    owner_identity = RNS.Identity.recall(OWNER)
    if owner_identity is None:
        print("owner identity unknown", flush=True)
        return
    owner_dest = RNS.Destination(
        owner_identity, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery"
    )
    lm = LXMF.LXMessage(owner_dest, dest, text.encode("utf-8"), title.encode("utf-8"),
                        desired_method=LXMF.LXMessage.DIRECT)
    router.handle_outbound(lm)
    print(f"sent: {text[:60]}", flush=True)


last_announce = time.time()
while True:
    for f in sorted(OUTBOX.glob("*.txt")):
        try:
            text = f.read_text().strip()
        finally:
            f.unlink()
        if text:
            send_to_owner(text)
    if time.time() - last_announce > 1800:
        router.announce(dest.hash)
        last_announce = time.time()
    time.sleep(1)
