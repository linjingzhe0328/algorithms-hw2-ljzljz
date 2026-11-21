"""A string-keyed hash table using separate chaining."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Generic, TypeVar

_Value = TypeVar("_Value")


class _Node(Generic[_Value]):
    def __init__(self, key: str, value: _Value, next_node: _Node[_Value] | None = None):
        self.key = key
        self.value = value
        self.next = next_node


class HashTable(Generic[_Value]):
    """Store key/value pairs in a resizable, separately chained hash table."""

    def __init__(
        self, initial_capacity: int = 11, max_load: float | None = 0.75
    ):
        if isinstance(initial_capacity, bool) or not isinstance(initial_capacity, int):
            raise TypeError("initial_capacity must be an integer")
        if initial_capacity <= 0:
            raise ValueError("initial_capacity must be positive")
        if max_load is not None:
            if isinstance(max_load, bool) or not isinstance(max_load, (int, float)):
                raise TypeError("max_load must be a number or None")
            if max_load <= 0:
                raise ValueError("max_load must be positive")

        self._buckets: list[_Node[_Value] | None] = [None] * initial_capacity
        self._size = 0
        self._max_load = max_load

    @property
    def capacity(self) -> int:
        return len(self._buckets)

    def __len__(self) -> int:
        return self._size

    def iter_buckets(self) -> Iterator[tuple[tuple[str, _Value], ...]]:
        """Yield each bucket's entries in chain order."""
        for bucket in self._buckets:
            entries = []
            node = bucket
            while node is not None:
                entries.append((node.key, node.value))
                node = node.next
            yield tuple(entries)

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

    @staticmethod
    def _string_hash(key: str) -> int:
        value = 0
        for character in key:
            value = value * 31 + ord(character)
        return value

    def _bucket_index(self, key: str) -> int:
        return self._string_hash(key) % self.capacity

    def put(self, key: str, value: _Value) -> None:
        self._validate_key(key)
        index = self._bucket_index(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        self._buckets[index] = _Node(key, value, self._buckets[index])
        self._size += 1
        if self._max_load is not None and self._size / self.capacity > self._max_load:
            self._resize(_next_prime(self.capacity * 2))

    def get(self, key: str) -> _Value | None:
        self._validate_key(key)
        node = self._buckets[self._bucket_index(key)]
        while node is not None:
            if node.key == key:
                return node.value
            node = node.next
        return None

    def delete(self, key: str) -> _Value:
        self._validate_key(key)
        index = self._bucket_index(key)
        previous = None
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                if previous is None:
                    self._buckets[index] = node.next
                else:
                    previous.next = node.next
                self._size -= 1
                return node.value
            previous = node
            node = node.next
        raise KeyError(key)

    def _resize(self, new_capacity: int) -> None:
        old_buckets = self._buckets
        self._buckets = [None] * new_capacity
        for bucket in old_buckets:
            node = bucket
            while node is not None:
                next_node = node.next
                index = self._bucket_index(node.key)
                self._buckets[index] = _Node(node.key, node.value, self._buckets[index])
                node = next_node


def _next_prime(minimum: int) -> int:
    candidate = max(2, minimum)
    if candidate > 2 and candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 1
    return True
