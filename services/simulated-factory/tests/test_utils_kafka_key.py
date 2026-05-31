from simulated_factory.utils import decode_kafka_key


def test_decode_kafka_key_none() -> None:
    assert decode_kafka_key(None) is None


def test_decode_kafka_key_utf8() -> None:
    assert decode_kafka_key(b"ord-1") == "ord-1"


def test_decode_kafka_key_non_utf8() -> None:
    data = bytes([0xFF, 0xFE])
    assert decode_kafka_key(data) == repr(bytes(data))
