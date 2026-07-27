from bridge.core import parse_outbound


def test_plain_text_is_broadcast():
    assert parse_outbound("yo homie") == (None, "yo homie")


def test_at_target_is_dm():
    assert parse_outbound("@OTG whats good") == ("OTG", "whats good")


def test_at_nodeid_is_dm():
    assert parse_outbound("@!a1b2c3d4 hey") == ("!a1b2c3d4", "hey")


def test_multiline_dm_keeps_body():
    target, msg = parse_outbound("@OTG line one\nline two")
    assert target == "OTG"
    assert msg == "line one\nline two"


def test_lone_at_word_is_broadcast():
    # "@name" with no message is not a DM command
    assert parse_outbound("@OTG") == (None, "@OTG")


def test_whitespace_stripped():
    assert parse_outbound("  hello  ") == (None, "hello")
