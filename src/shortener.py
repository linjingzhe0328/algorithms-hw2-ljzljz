"""In-memory URL shortening service."""

from urllib.parse import urlsplit

from src.base62 import decode, encode
from src.hash_table import HashTable


class URLShortener:
    """Map validated HTTP(S) URLs to sequential base62 codes."""

    def __init__(self):
        self._url_to_code: HashTable[str] = HashTable()
        self._code_to_url: HashTable[str] = HashTable()
        self._next_id = 0

    def shorten(self, url: str) -> str:
        self._validate_url(url)

        existing_code = self._url_to_code.get(url)
        if existing_code is not None:
            return existing_code

        code = encode(self._next_id)
        self._next_id += 1
        self._url_to_code.put(url, code)
        self._code_to_url.put(code, url)
        return code

    def expand(self, code: str) -> str:
        decode(code)
        url = self._code_to_url.get(code)
        if url is None:
            raise KeyError(code)
        return url

    @staticmethod
    def _validate_url(url: str) -> None:
        if not isinstance(url, str):
            raise TypeError("url must be a string")
        if not url or any(character.isspace() for character in url):
            raise ValueError("url must be non-empty and contain no whitespace")

        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
            _ = parsed.port
        except ValueError as error:
            raise ValueError("invalid URL") from error

        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc or not hostname:
            raise ValueError("url must be an absolute HTTP or HTTPS URL with a host")
