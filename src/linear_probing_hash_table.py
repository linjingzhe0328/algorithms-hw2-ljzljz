"""A string-keyed hash table using linear probing."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Generic, TypeVar

from src.hash_table import HashTable, _next_prime

_Value = TypeVar("_Value")


class _Deleted:
    pass


class _Entry(Generic[_Value]):
    def __init__(self, key: str, value: _Value):
        self.key = key
        self.value = value


_DELETED = _Deleted()


class LinearProbingHashTable(Generic[_Value]):
    """Store key/value pairs in a resizable, linearly probed hash table."""

    def __init__(
        self, initial_capacity: int = 11, max_load: float | None = 0.75
    ):
        self._validate_capacity(initial_capacity, max_load)
        self._slots: list[_Entry[_Value] | _Deleted | None] = [
            None
        ] * initial_capacity
        self._size = 0
        self._max_load = max_load

    @property
    def capacity(self) -> int:
        return len(self._slots)

    def __len__(self) -> int:
        return self._size

    def iter_buckets(self) -> Iterator[tuple[tuple[str, _Value], ...]]:
        """Yield each slot's entry as a one-item bucket, matching HashTable."""
        for slot in self._slots:
            if isinstance(slot, _Entry):
                yield ((slot.key, slot.value),)
            else:
                yield ()

    @staticmethod
    def _validate_capacity(initial_capacity: int, max_load: float | None) -> None:
        if isinstance(initial_capacity, bool) or not isinstance(initial_capacity, int):
            raise TypeError("initial_capacity must be an integer")
        if initial_capacity <= 0:
            raise ValueError("initial_capacity must be positive")
        if max_load is not None:
            if isinstance(max_load, bool) or not isinstance(max_load, (int, float)):
                raise TypeError("max_load must be a number or None")
            if max_load <= 0:
                raise ValueError("max_load must be positive")

    @staticmethod
    def _validate_key(key: str) -> None:
        HashTable._validate_key(key)

    @staticmethod
    def _string_hash(key: str) -> int:
        return HashTable._string_hash(key)

    def _bucket_index(self, key: str) -> int:
        return self._string_hash(key) % self.capacity

    def probe_indices(self, key: str) -> tuple[int, ...]:
        """Return the slots inspected when looking up key."""
        self._validate_key(key)
        inspected = []
        for index in self._probe_order(key):
            inspected.append(index)
            slot = self._slots[index]
            if slot is None or (
                isinstance(slot, _Entry) and slot.key == key
            ):
                break
        return tuple(inspected)

    def put(self, key: str, value: _Value) -> None:
        self._validate_key(key)
        first_deleted = None
        for index in self._probe_order(key):
            slot = self._slots[index]
            if isinstance(slot, _Entry):
                if slot.key == key:
                    slot.value = value
                    return
            elif slot is _DELETED:
                if first_deleted is None:
                    first_deleted = index
            else:
                self._insert_at(first_deleted if first_deleted is not None else index, key, value)
                return

        if first_deleted is None:
            raise OverflowError("hash table is full")
        self._insert_at(first_deleted, key, value)

    def get(self, key: str) -> _Value | None:
        self._validate_key(key)
        for index in self._probe_order(key):
            slot = self._slots[index]
            if slot is None:
                return None
            if isinstance(slot, _Entry) and slot.key == key:
                return slot.value
        return None

    def delete(self, key: str) -> _Value:
        self._validate_key(key)
        for index in self._probe_order(key):
            slot = self._slots[index]
            if slot is None:
                break
            if isinstance(slot, _Entry) and slot.key == key:
                self._slots[index] = _DELETED
                self._size -= 1
                return slot.value
        raise KeyError(key)

    def _probe_order(self, key: str) -> Iterator[int]:
        start = self._bucket_index(key)
        for offset in range(self.capacity):
            yield (start + offset) % self.capacity

    def _insert_at(self, index: int, key: str, value: _Value) -> None:
        self._slots[index] = _Entry(key, value)
        self._size += 1
        if self._max_load is not None and self._size / self.capacity > self._max_load:
            self._resize(_next_prime(self.capacity * 2))

    def _resize(self, new_capacity: int) -> None:
        old_slots = self._slots
        self._slots = [None] * new_capacity
        for slot in old_slots:
            if isinstance(slot, _Entry):
                start = self._bucket_index(slot.key)
                for offset in range(self.capacity):
                    index = (start + offset) % self.capacity
                    if self._slots[index] is None:
                        self._slots[index] = _Entry(slot.key, slot.value)
                        break
