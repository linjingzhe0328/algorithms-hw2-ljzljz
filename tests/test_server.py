import json
from http.client import HTTPConnection
from http.server import HTTPServer
import threading
import unittest
from urllib.parse import urlencode

from src.server import ShortenerHandler
from src.shortener import URLShortener


class ShortenerServerTests(unittest.TestCase):
    def setUp(self):
        ShortenerHandler.shortener = URLShortener()
        self.server = HTTPServer(("127.0.0.1", 0), ShortenerHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = HTTPConnection("127.0.0.1", self.server.server_port)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        self.connection.request(method, path, body=body, headers=headers or {})
        response = self.connection.getresponse()
        return response.status, response.getheader("Content-Type"), response.getheader("Location"), response.read()

    def test_home_form_and_shortening_redirect(self):
        status, content_type, _, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn('name="url"', body.decode("utf-8"))

        form = urlencode({"url": "https://example.com/path"})
        status, _, _, body = self.request(
            "POST",
            "/",
            body=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 201)
        self.assertIn("http://127.0.0.1:", body.decode("utf-8"))
        self.assertIn("/0</a>", body.decode("utf-8"))

        status, _, location, _ = self.request("GET", "/0")
        self.assertEqual(status, 302)
        self.assertEqual(location, "https://example.com/path")

    def test_table_shows_chained_entries_and_horner_steps(self):
        ShortenerHandler.shortener.shorten("https://a.com")
        ShortenerHandler.shortener.shorten("https://l.com")

        status, _, _, body = self.request("GET", "/table")
        page = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn("URL 키", page)
        self.assertIn("짧은 코드", page)
        self.assertIn("짧은 링크", page)
        self.assertIn("호너 해시 계산 과정", page)
        self.assertIn("(31 * 0 + ord(&#x27;h&#x27;)) % 11 = 5", page)
        self.assertIn("(31 * 5 + ord(&#x27;t&#x27;)) % 11", page)
        self.assertIn(" → ", page)

    def test_table_shows_linear_probe_path_and_horner_steps(self):
        ShortenerHandler.shortener = URLShortener("linear_probing")
        ShortenerHandler.shortener.shorten("https://a.com")
        ShortenerHandler.shortener.shorten("https://l.com")

        status, _, _, body = self.request("GET", "/table")
        page = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn("선형 탐지", page)
        self.assertIn("선형 탐지 순서", page)
        self.assertIn("칸 8 확인", page)
        self.assertIn("칸 9 확인 (저장된 키)", page)
        self.assertIn("(31 * 0 + ord(&#x27;h&#x27;)) % 11 = 5", page)

    def test_short_links_use_forwarded_codespaces_address(self):
        proxy_headers = {
            "X-Forwarded-Host": "my-codespace-8000.app.github.dev, internal",
            "X-Forwarded-Proto": "https, http",
        }
        short_link = "https://my-codespace-8000.app.github.dev/0"
        form = urlencode({"url": "https://example.com/path"})
        status, _, _, body = self.request(
            "POST",
            "/",
            body=form,
            headers=proxy_headers,
        )
        self.assertEqual(status, 201)
        self.assertIn(f'href="{short_link}"', body.decode("utf-8"))

        status, _, _, body = self.request("GET", "/table", headers=proxy_headers)
        self.assertEqual(status, 200)
        self.assertIn(f'href="{short_link}"', body.decode("utf-8"))

    def test_json_api_and_invalid_requests(self):
        body = json.dumps({"url": "https://example.com"})
        status, content_type, _, response_body = self.request(
            "POST",
            "/api/shorten",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 201)
        self.assertIn("application/json", content_type)
        self.assertEqual(json.loads(response_body), {
            "code": "0",
            "short_url": f"http://127.0.0.1:{self.server.server_port}/0",
        })

        status, _, _, response_body = self.request(
            "POST",
            "/api/shorten",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(response_body)["code"], "0")

        status, _, _, response_body = self.request(
            "POST",
            "/api/shorten",
            body="{",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(response_body))

        status, _, _, response_body = self.request("GET", "/api/expand/missing")
        self.assertEqual(status, 404)
        self.assertIn("error", json.loads(response_body))


if __name__ == "__main__":
    unittest.main()
