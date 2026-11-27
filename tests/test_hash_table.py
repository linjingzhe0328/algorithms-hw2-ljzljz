import unittest

from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable


class HashTableTests(unittest.TestCase):
    table_class = HashTable
    no_resize_entries = 10

    def test_empty_table_lookup_returns_none(self):
        table = self.table_class()

        self.assertIsNone(table.get("missing"))

    def test_put_updates_existing_key_without_adding_an_entry(self):
        table = self.table_class()

        table.put("key", "first")
        table.put("key", "updated")

        self.assertEqual(table.get("key"), "updated")
        self.assertEqual(len(table), 1)

    def test_colliding_keys_can_both_be_retrieved(self):
        table = self.table_class()

        # With the specified Horner hash and initial capacity 11, these keys collide.
        table.put("a", "value-a")
        table.put("l", "value-l")

        self.assertEqual(table.get("a"), "value-a")
        self.assertEqual(table.get("l"), "value-l")

    def test_resize_threshold_and_rehash_preserve_entries(self):
        table = self.table_class()

        for index in range(8):
            table.put(f"key-{index}", f"value-{index}")
        self.assertEqual(table.capacity, 11)

        table.put("key-8", "value-8")
        self.assertEqual(table.capacity, 23)

        for index in range(9):
            with self.subTest(index=index):
                self.assertEqual(table.get(f"key-{index}"), f"value-{index}")

    def test_custom_capacity_and_disabled_resize(self):
        table = self.table_class(initial_capacity=5, max_load=None)

        for index in range(self.no_resize_entries):
            table.put(f"key-{index}", f"value-{index}")

        self.assertEqual(table.capacity, 5)
        self.assertEqual(len(table), self.no_resize_entries)
        for index in range(self.no_resize_entries):
            with self.subTest(index=index):
                self.assertEqual(table.get(f"key-{index}"), f"value-{index}")


class LinearProbingHashTableTests(HashTableTests):
    table_class = LinearProbingHashTable
    no_resize_entries = 5

    def test_probe_wraps_from_last_slot_to_zero(self):
        table = self.table_class(initial_capacity=5, max_load=None)

        table.put("h", "last")
        table.put("m", "wrapped")

        buckets = list(table.iter_buckets())
        self.assertEqual(buckets[4], (("h", "last"),))
        self.assertEqual(buckets[0], (("m", "wrapped"),))
        self.assertEqual(table.probe_indices("m"), (4, 0))
        self.assertEqual(table.get("m"), "wrapped")

    def test_full_table_rejects_an_additional_key_without_losing_entries(self):
        table = self.table_class(initial_capacity=3, max_load=None)
        for key in ("a", "b", "c"):
            table.put(key, key.upper())

        with self.assertRaises(OverflowError):
            table.put("d", "D")

        self.assertEqual(len(table), 3)
        for key in ("a", "b", "c"):
            with self.subTest(key=key):
                self.assertEqual(table.get(key), key.upper())

    def test_deleting_a_colliding_key_keeps_later_entries_reachable(self):
        table = self.table_class(initial_capacity=5, max_load=None)
        table.put("h", "first")
        table.put("m", "second")

        self.assertEqual(table.delete("h"), "first")
        self.assertEqual(table.get("m"), "second")
        table.put("r", "reused tombstone")
        self.assertEqual(table.get("r"), "reused tombstone")
        self.assertEqual(len(table), 2)


if __name__ == "__main__":
    unittest.main()
