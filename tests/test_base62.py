import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_encode_known_values(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")
        self.assertEqual(encode(3843), "ZZ")

    def test_decode_known_values(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)
        self.assertEqual(decode("ZZ"), 3843)

    def test_round_trip_large_integer(self):
        value = 2**256
        self.assertEqual(decode(encode(value)), value)

    def test_encode_rejects_negative_and_non_integer_values(self):
        with self.assertRaises(ValueError):
            encode(-1)
        for value in (1.5, True):
            with self.subTest(value=value), self.assertRaises(TypeError):
                encode(value)

    def test_decode_rejects_empty_and_invalid_strings(self):
        for value in ("", "a!", "é"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode(value)

    def test_decode_rejects_non_string_values(self):
        with self.assertRaises(TypeError):
            decode(62)


if __name__ == "__main__":
    unittest.main()
