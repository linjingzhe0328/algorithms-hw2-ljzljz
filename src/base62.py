"""Encode and decode non-negative integers using the 0-9, a-z, A-Z alphabet."""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_CHAR_TO_VALUE = {character: value for value, character in enumerate(ALPHABET)}


def encode(value: int) -> str:
    """Return the base62 representation of a non-negative integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("value must be an integer")
    if value < 0:
        raise ValueError("value must be non-negative")
    if value == 0:
        return ALPHABET[0]

    encoded = []
    while value:
        value, remainder = divmod(value, len(ALPHABET))
        encoded.append(ALPHABET[remainder])
    return "".join(reversed(encoded))


def decode(encoded: str) -> int:
    """Return the integer represented by a base62 string."""
    if not isinstance(encoded, str):
        raise TypeError("encoded value must be a string")
    if not encoded:
        raise ValueError("encoded value must not be empty")

    value = 0
    for character in encoded:
        try:
            digit = _CHAR_TO_VALUE[character]
        except KeyError:
            raise ValueError(f"invalid base62 character: {character!r}") from None
        value = value * len(ALPHABET) + digit
    return value
