from bridge.nodecache import NodeCache


def make_cache():
    c = NodeCache()
    c.update("!a1b2c3d4", "OTG", "Otis The Great")
    c.update("!deadbeef", "HMB", "Homeboy")
    return c


def test_resolve_by_short_name_case_insensitive():
    assert make_cache().resolve("otg") == "!a1b2c3d4"


def test_resolve_by_long_name():
    assert make_cache().resolve("Homeboy") == "!deadbeef"


def test_resolve_by_node_id_passthrough():
    assert make_cache().resolve("!12345678") == "!12345678"


def test_resolve_unknown_returns_none():
    assert make_cache().resolve("nobody") is None


def test_label_prefers_short_name():
    assert make_cache().label("!a1b2c3d4") == "OTG"


def test_label_unknown_falls_back_to_id():
    assert make_cache().label("!99999999") == "!99999999"


def test_partial_update_keeps_existing_fields():
    c = make_cache()
    c.update("!a1b2c3d4", None, "Renamed Long")
    assert c.label("!a1b2c3d4") == "OTG"
    assert c.resolve("Renamed Long") == "!a1b2c3d4"
