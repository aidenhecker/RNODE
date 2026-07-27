import logging
import re

log = logging.getLogger("bridge.core")

DM_PATTERN = re.compile(r"^@(\S+)\s+(.+)$", re.DOTALL)


def parse_outbound(text: str) -> tuple[str | None, str]:
    """'@target message' -> (target, message); plain text -> (None, text)."""
    m = DM_PATTERN.match(text.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return None, text.strip()


class Bridge:
    """Wires MeshtasticLink and LXMFLink together.

    mesh -> LXMF : every text heard on the mesh is delivered to the owner,
                   labelled with the sender and DM/broadcast marker.
    LXMF -> mesh : owner sends '@node message' for a Meshtastic DM,
                   plain text for a channel-0 broadcast,
                   '/nodes' to list the node directory.
    """

    def __init__(self, mesh_link, lxmf_link):
        self.mesh = mesh_link
        self.lxmf = lxmf_link

    # mesh -> LXMF
    def on_mesh_text(self, from_id: str, label: str, text: str, is_dm: bool):
        kind = "DM" if is_dm else "bcast"
        log.info("mesh->lxmf [%s] %s: %s", kind, label, text)
        self.lxmf.send_to_owner(f"[{label}{' → you' if is_dm else ''}] {text}",
                                title=f"Meshtastic {kind}")

    # LXMF -> mesh
    def on_lxmf_text(self, text: str):
        if text.strip() == "/nodes":
            nodes = self.mesh.nodes.all()
            listing = "\n".join(
                f"{nid}  {e['short'] or '-'}  {e['long'] or '-'}" for nid, e in sorted(nodes.items())
            ) or "(no nodes heard yet)"
            self.lxmf.send_to_owner(listing, title="Node directory")
            return

        target, message = parse_outbound(text)
        if not message:
            return
        try:
            if target is None:
                log.info("lxmf->mesh [bcast]: %s", message)
                self.mesh.send_broadcast(message)
            else:
                node_id = self.mesh.nodes.resolve(target)
                if node_id is None:
                    self.lxmf.send_to_owner(
                        f"Unknown node '@{target}'. Send /nodes for the directory.",
                        title="Bridge error",
                    )
                    return
                log.info("lxmf->mesh [DM %s]: %s", node_id, message)
                self.mesh.send_dm(node_id, message)
        except ConnectionError as e:
            self.lxmf.send_to_owner(f"Mesh link is down: {e}", title="Bridge error")
