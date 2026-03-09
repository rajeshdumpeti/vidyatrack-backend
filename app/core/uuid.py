import secrets
import time
import uuid


def uuid7() -> uuid.UUID:
    """
    Generate a UUIDv7 (time-ordered) per RFC 9562.

    Layout:
    - 48 bits: Unix time in milliseconds
    - 4 bits: version (0b0111)
    - 12 bits: random
    - 2 bits: variant (0b10)
    - 62 bits: random
    """
    ms = int(time.time() * 1000)
    time_high = ms & ((1 << 48) - 1)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    version = 0x7
    variant = 0b10
    uuid_int = (
        (time_high << 80)
        | (version << 76)
        | (rand_a << 64)
        | (variant << 62)
        | rand_b
    )
    return uuid.UUID(int=uuid_int)
