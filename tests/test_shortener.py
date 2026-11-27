import unittest

from src.shortener import URLShortener


class URLShortenerTests(unittest.TestCase):
    collision_strategy = "chaining"

    def setUp(self):
        self.shortener = URLShortener(self.collision_strategy)

    def test_shorten_accepts_http_and_https_urls(self):
        http_code = self.shortener.shorten("http://example.com")
        https_code = self.shortener.shorten("https://example.org")

        self.assertEqual(http_code, "0")
        self.assertEqual(https_code, "1")

    def test_shorten_same_url_returns_existing_code(self):
        url = "https://example.com/path"

        first_code = self.shortener.shorten(url)
        second_code = self.shortener.shorten(url)

        self.assertEqual(first_code, second_code)

    def test_shorten_distinct_url_strings_get_distinct_sequential_codes(self):
        first_code = self.shortener.shorten("https://example.com")
        second_code = self.shortener.shorten("https://example.com/")

        self.assertEqual(first_code, "0")
        self.assertEqual(second_code, "1")

    def test_shorten_rejects_invalid_urls(self):
        invalid_urls = (
            "",
            "https://example.com/a b",
            "https://example.com/a\tb",
            "https://",
            "https:///path",
            "ftp://example.com",
            "example.com",
        )
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.shortener.shorten(url)

    def test_shorten_rejects_non_string_input(self):
        for url in (None, 42):
            with self.subTest(url=url), self.assertRaises(TypeError):
                self.shortener.shorten(url)

    def test_expand_registered_code_returns_original_url(self):
        url = "https://example.com/a?query=value"
        code = self.shortener.shorten(url)

        self.assertEqual(self.shortener.expand(code), url)

    def test_expand_rejects_malformed_base62_code(self):
        for code in ("", "bad-code!"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.shortener.expand(code)

    def test_expand_rejects_valid_but_unregistered_code(self):
        with self.assertRaises(KeyError):
            self.shortener.expand("Z")

    def test_new_shortener_has_no_previous_instance_mappings(self):
        code = self.shortener.shorten("https://example.com")
        restarted_shortener = URLShortener(self.collision_strategy)

        with self.assertRaises(KeyError):
            restarted_shortener.expand(code)


class LinearProbingURLShortenerTests(URLShortenerTests):
    collision_strategy = "linear_probing"

    def test_unknown_collision_strategy_is_rejected(self):
        with self.assertRaises(ValueError):
            URLShortener(collision_strategy="unknown")


if __name__ == "__main__":
    unittest.main()
