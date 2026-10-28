"""Fail the build if generated HTML references missing local CSS or JavaScript."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("src"):
            self.urls.append(attrs["src"])
        elif tag == "link" and "stylesheet" in attrs.get("rel", "").split():
            if attrs.get("href"):
                self.urls.append(attrs["href"])


def main():
    root = Path("site").resolve()
    if not (root / "index.html").is_file():
        raise SystemExit("Missing site/index.html")
    missing = []
    count = 0
    for page in root.rglob("*.html"):
        parser = Assets()
        parser.feed(page.read_text(encoding="utf-8"))
        for url in parser.urls:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            path = unquote(parts.path)
            target = (
                root / path.lstrip("/") if path.startswith("/") else page.parent / path
            ).resolve()
            count += 1
            if (
                not target.is_relative_to(root)
                or not target.is_file()
                or not target.stat().st_size
            ):
                missing.append(f"{page.relative_to(root)}: {url}")
    if missing:
        raise SystemExit("Missing or empty local assets:\n" + "\n".join(missing))
    if not count:
        raise SystemExit("No local assets found")
    print(f"Verified {count} local asset references")


if __name__ == "__main__":
    main()
