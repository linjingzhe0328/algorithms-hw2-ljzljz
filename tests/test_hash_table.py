import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_empty_table_lookup_returns_none(self):
        table = HashTable()

        self.assertIsNone(table.get("missing"))

    def test_put_updates_existing_key_without_adding_an_entry(self):
        table = HashTable()

        table.put("key", "first")
        table.put("key", "updated")

        self.assertEqual(table.get("key"), "updated")
        self.assertEqual(len(table), 1)

    def test_colliding_keys_can_both_be_retrieved(self):
        table = HashTable()

        # With the specified Horner hash and initial capacity 11, these keys collide.
        table.put("a", "value-a")
        table.put("l", "value-l")

        self.assertEqual(table.get("a"), "value-a")
        self.assertEqual(table.get("l"), "value-l")

    def test_resize_threshold_and_rehash_preserve_entries(self):
        table = HashTable()

        for index in range(8):
            table.put(f"key-{index}", f"value-{index}")
        self.assertEqual(table.capacity, 11)

        table.put("key-8", "value-8")
        self.assertEqual(table.capacity, 23)

        for index in range(9):
            with self.subTest(index=index):
                self.assertEqual(table.get(f"key-{index}"), f"value-{index}")


if __name__ == "__main__":
    unittest.main()
