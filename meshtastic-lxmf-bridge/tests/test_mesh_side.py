from bridge.config import MeshtasticConfig
from bridge.mesh_side import MeshtasticLink


def make_link(received):
    cfg = MeshtasticConfig(connection="serial", port="/dev/fake")
    return MeshtasticLink(cfg, on_text=lambda *a: received.append(a),
                          interface_factory=lambda: None)


def text_packet(from_id, to_id, text):
    return {
        "fromId": from_id,
        "toId": to_id,
        "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": text},
    }


def test_broadcast_text_dispatched():
    received = []
    link = make_link(received)
    link._on_receive(text_packet("!a1b2c3d4", "^all", "hey all"))
    assert received == [("!a1b2c3d4", "!a1b2c3d4", "hey all", False)]


def test_dm_text_dispatched_as_dm():
    received = []
    link = make_link(received)
    link._on_receive(text_packet("!a1b2c3d4", "!mybridge", "just you"))
    assert received[0][3] is True


def test_own_echo_ignored():
    received = []
    link = make_link(received)
    link.my_id = "!a1b2c3d4"
    link._on_receive(text_packet("!a1b2c3d4", "^all", "echo"))
    assert received == []


def test_nodeinfo_updates_cache_not_dispatched():
    received = []
    link = make_link(received)
    link._on_receive({
        "fromId": "!deadbeef",
        "toId": "^all",
        "decoded": {"portnum": "NODEINFO_APP",
                    "user": {"shortName": "HMB", "longName": "Homeboy"}},
    })
    assert received == []
    assert link.nodes.resolve("HMB") == "!deadbeef"


def test_non_text_ports_ignored():
    received = []
    link = make_link(received)
    link._on_receive({"fromId": "!deadbeef", "toId": "^all",
                      "decoded": {"portnum": "POSITION_APP"}})
    assert received == []


def test_malformed_packet_does_not_raise():
    received = []
    link = make_link(received)
    link._on_receive({})
    assert received == []
