from bridge.core import Bridge
from bridge.nodecache import NodeCache


class FakeMesh:
    def __init__(self):
        self.nodes = NodeCache()
        self.broadcasts = []
        self.dms = []
        self.down = False

    def send_broadcast(self, text):
        if self.down:
            raise ConnectionError("link down")
        self.broadcasts.append(text)

    def send_dm(self, dest_id, text):
        if self.down:
            raise ConnectionError("link down")
        self.dms.append((dest_id, text))


class FakeLXMF:
    def __init__(self):
        self.sent = []

    def send_to_owner(self, text, title=""):
        self.sent.append((title, text))
        return True


def make_bridge():
    mesh, lxmf = FakeMesh(), FakeLXMF()
    mesh.nodes.update("!a1b2c3d4", "OTG", "Otis The Great")
    return Bridge(mesh, lxmf), mesh, lxmf


def test_mesh_broadcast_reaches_owner_with_label():
    bridge, _, lxmf = make_bridge()
    bridge.on_mesh_text("!a1b2c3d4", "OTG", "sup", is_dm=False)
    title, text = lxmf.sent[0]
    assert title == "Meshtastic bcast"
    assert text == "[OTG] sup"


def test_mesh_dm_is_marked():
    bridge, _, lxmf = make_bridge()
    bridge.on_mesh_text("!a1b2c3d4", "OTG", "yo just you", is_dm=True)
    title, text = lxmf.sent[0]
    assert title == "Meshtastic DM"
    assert "→ you" in text


def test_owner_plain_text_broadcasts():
    bridge, mesh, _ = make_bridge()
    bridge.on_lxmf_text("hello mesh")
    assert mesh.broadcasts == ["hello mesh"]


def test_owner_at_short_name_sends_dm():
    bridge, mesh, _ = make_bridge()
    bridge.on_lxmf_text("@otg you up?")
    assert mesh.dms == [("!a1b2c3d4", "you up?")]


def test_owner_at_unknown_gets_error_reply():
    bridge, mesh, lxmf = make_bridge()
    bridge.on_lxmf_text("@ghost boo")
    assert mesh.dms == []
    assert lxmf.sent[0][0] == "Bridge error"


def test_nodes_command_returns_directory():
    bridge, _, lxmf = make_bridge()
    bridge.on_lxmf_text("/nodes")
    title, text = lxmf.sent[0]
    assert title == "Node directory"
    assert "!a1b2c3d4" in text and "OTG" in text


def test_mesh_down_reports_error_to_owner():
    bridge, mesh, lxmf = make_bridge()
    mesh.down = True
    bridge.on_lxmf_text("hello mesh")
    assert lxmf.sent[0][0] == "Bridge error"
