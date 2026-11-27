"""HTTP interface for the in-memory URL shortener."""

from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import parse_qsl, urlsplit

from src.shortener import URLShortener

_MAX_REQUEST_BYTES = 1_000_000
shortener = URLShortener()


class ShortenerHandler(BaseHTTPRequestHandler):
    """Serve the browser UI and JSON API for a URLShortener."""

    shortener = shortener

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self._send_html(200, _page("URL 단축기", _form()))
        elif path == "/table":
            self._send_html(200, self._table_page())
        elif path.startswith("/api/expand/"):
            self._expand(path[len("/api/expand/") :], as_json=True)
        elif path.startswith("/api/"):
            self._send_json_error(404, "찾을 수 없는 API 경로입니다.")
        else:
            code = path[1:] if path.startswith("/") else path
            self._expand(code, as_json=False)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/shorten":
            self._shorten_api()
        elif path == "/":
            self._shorten_form()
        elif path.startswith("/api/"):
            self._send_json_error(404, "찾을 수 없는 API 경로입니다.")
        else:
            self._send_html(404, _page("찾을 수 없음", "<p>페이지를 찾을 수 없습니다.</p>"))

    def _shorten_api(self) -> None:
        body = self._read_body()
        if body is None:
            return
        try:
            payload = json.loads(body.decode("utf-8"), object_pairs_hook=tuple)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json_error(400, "올바른 JSON 요청 본문이 필요합니다.")
            return

        url = None
        if isinstance(payload, tuple):
            for pair in payload:
                if isinstance(pair, tuple) and len(pair) == 2 and pair[0] == "url":
                    url = pair[1]
                    break
        if not isinstance(url, str):
            self._send_json_error(400, "url 문자열이 필요합니다.")
            return

        existing_code = self.shortener._url_to_code.get(url)
        try:
            code = self.shortener.shorten(url)
        except (TypeError, ValueError) as error:
            self._send_json_error(400, str(error))
            return

        status = 200 if existing_code is not None else 201
        short_url = self._short_url(code)
        response = (
            '{"code":'
            + json.dumps(code)
            + ',"short_url":'
            + json.dumps(short_url)
            + "}"
        )
        self._send_json(status, response)

    def _shorten_form(self) -> None:
        body = self._read_body()
        if body is None:
            return
        try:
            form = parse_qsl(body.decode("utf-8"), keep_blank_values=True, max_num_fields=100)
        except (UnicodeDecodeError, ValueError):
            self._send_html(400, _page("잘못된 요청", _form("요청을 읽을 수 없습니다.")))
            return

        url = None
        for name, value in form:
            if name == "url":
                url = value
                break
        if url is None:
            self._send_html(400, _page("잘못된 URL", _form("URL을 입력해 주세요.")))
            return

        existing_code = self.shortener._url_to_code.get(url)
        try:
            code = self.shortener.shorten(url)
        except (TypeError, ValueError) as error:
            self._send_html(400, _page("잘못된 URL", _form(str(error), url)))
            return

        status = 200 if existing_code is not None else 201
        short_url = escape(self._short_url(code), quote=True)
        content = (
            "<h1>짧은 URL 결과</h1>"
            f'<p><a class="short-link" href="{short_url}">{short_url}</a></p>'
            '<p><a href="/">다른 URL 줄이기</a> · <a href="/table">해시 테이블 보기</a></p>'
        )
        self._send_html(status, _page("짧은 URL 결과", content))

    def _expand(self, code: str, as_json: bool) -> None:
        try:
            url = self.shortener.expand(code)
        except (TypeError, ValueError, KeyError):
            if as_json:
                self._send_json_error(404, "등록된 짧은 코드가 없습니다.")
            else:
                self._send_html(
                    404,
                    _page("찾을 수 없음", "<p>등록된 짧은 URL이 아닙니다.</p><p><a href=\"/\">돌아가기</a></p>"),
                )
            return

        if as_json:
            self._send_json(200, '{"url":' + json.dumps(url) + "}")
        else:
            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def _table_page(self) -> str:
        table = self.shortener._url_to_code
        buckets = []
        for index, entries in enumerate(table.iter_buckets()):
            nodes = []
            for key, code in entries:
                nodes.append(self._table_node(key, code, index))
            if not nodes:
                chain = '<span class="empty">비어 있음</span>'
            else:
                chain = '<span class="arrow"> → </span>'.join(nodes)
            buckets.append(
                f'<section class="bucket"><h2>칸 {index}</h2><div class="chain">{chain}</div></section>'
            )
        content = (
            "<h1>URL → 짧은 코드 해시 테이블</h1>"
            f"<p>칸 수: {table.capacity} · 저장된 URL: {len(table)}</p>"
            '<p><a href="/">URL 줄이기</a></p>'
            '<div class="buckets">'
            + "".join(buckets)
            + "</div>"
        )
        return _page("해시 테이블", content)

    def _table_node(self, key: str, code: str, bucket_index: int) -> str:
        escaped_key = escape(key)
        short_url = escape(self._short_url(code), quote=True)
        modulus = self.shortener._url_to_code.capacity
        hash_value = 0
        steps = []
        for character in key:
            previous = hash_value
            character_code = ord(character)
            hash_value = (31 * previous + character_code) % modulus
            steps.append(
                "<li>"
                f"(31 * {previous} + ord({escape(repr(character))})) "
                f"% {modulus} = {hash_value}"
                "</li>"
            )
        trace = (
            "<p>호너 해시: "
            f"<code>{hash_value}</code> mod {modulus} "
            f"= 칸 {bucket_index}</p><ol>{''.join(steps)}</ol>"
        )
        return (
            '<article class="node">'
            f"<p><strong>URL 키</strong>: <code>{escaped_key}</code></p>"
            f"<p><strong>짧은 코드</strong>: <code>{escape(code)}</code></p>"
            f'<p><strong>짧은 링크</strong>: <a href="{short_url}">{short_url}</a></p>'
            f"<details><summary>호너 해시 계산 과정</summary>{trace}</details>"
            "</article>"
        )

    def _short_url(self, code: str) -> str:
        forwarded_host = self.headers.get("X-Forwarded-Host", "")
        host = forwarded_host.split(",", 1)[0].strip() or self.headers.get(
            "Host", "localhost:8000"
        )
        forwarded_proto = self.headers.get("X-Forwarded-Proto", "")
        scheme = "https" if forwarded_proto.split(",", 1)[0].strip().lower() == "https" else "http"
        return f"{scheme}://{host}/{code}"

    def _read_body(self) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json_error(400, "Content-Length가 올바르지 않습니다.")
            return None
        if length < 0:
            self._send_json_error(400, "Content-Length가 올바르지 않습니다.")
            return None
        if length > _MAX_REQUEST_BYTES:
            self._send_json_error(413, "요청 본문이 너무 큽니다.")
            return None
        return self.rfile.read(length)

    def _send_html(self, status: int, content: str) -> None:
        self._send_bytes(status, content.encode("utf-8"), "text/html; charset=utf-8")

    def _send_json(self, status: int, content: str) -> None:
        self._send_bytes(status, content.encode("utf-8"), "application/json; charset=utf-8")

    def _send_json_error(self, status: int, message: str) -> None:
        self._send_json(status, '{"error":' + json.dumps(message, ensure_ascii=False) + "}")

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _page(title: str, content: str) -> str:
    return (
        "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title>"
        "<style>"
        "body{font:16px system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem}"
        "input[type=url]{box-sizing:border-box;width:min(100%,40rem);padding:.7rem}"
        "button{padding:.7rem 1rem;margin-top:.7rem}"
        ".buckets{display:grid;gap:.8rem}.bucket{border:1px solid #bbb;padding:.8rem}"
        ".chain{display:flex;align-items:stretch;flex-wrap:wrap;gap:.5rem}"
        ".node{border:1px solid #888;border-radius:.4rem;padding:.6rem;overflow-wrap:anywhere}"
        ".arrow{align-self:center;font-size:1.4rem}.empty{color:#777}"
        "details{margin-top:.7rem}code{overflow-wrap:anywhere}"
        "</style></head><body>"
        + content
        + "</body></html>"
    )


def _form(message: str = "", value: str = "") -> str:
    escaped_value = escape(value, quote=True)
    error = f'<p role="alert">{escape(message)}</p>' if message else ""
    return (
        "<h1>URL 단축기</h1>"
        f"{error}<form method=\"post\" action=\"/\">"
        '<label for="url">줄일 URL</label><br>'
        f'<input id="url" name="url" type="url" required value="{escaped_value}" '
        'placeholder="https://example.com">'
        '<br><button type="submit">줄이기</button></form>'
        '<p><a href="/table">현재 해시 테이블 보기</a></p>'
    )


def main() -> None:
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Run the URL shortener web server.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = HTTPServer(("", args.port), ShortenerHandler)
    print(f"Serving URL shortener on port {args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
