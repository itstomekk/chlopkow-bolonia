"""Check the local page identity and its browser-share metadata."""
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"
TITLE = "CHŁOPKÓW POLONIA"
DESCRIPTION = "CHŁOPKÓW POLONIA - pikselowa przygoda przez prawdziwą wieś."
REQUIRED_SCRIPTS = {"js/chat.js", "js/world-life.js", "js/cemetery-art.js"}


class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta = {}
        self.links = []
        self.scripts = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = attrs.get("name") or attrs.get("property")
            if key and "content" in attrs:
                self.meta[key] = attrs["content"]
        elif tag == "link":
            self.links.append(attrs)
        elif tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


html = INDEX.read_text(encoding="utf-8")
parser = HeadParser()
parser.feed(html)

assert parser.title == TITLE, parser.title
assert parser.meta["description"] == DESCRIPTION
assert parser.meta["og:title"] == TITLE
assert parser.meta["og:description"] == DESCRIPTION
assert parser.meta["og:type"] == "website"
assert parser.meta["og:image"] == "img/og-polonia.png"
assert (ROOT / "docs" / parser.meta["og:image"]).is_file()
assert set(REQUIRED_SCRIPTS).issubset(parser.scripts)
assert all((ROOT / "docs" / src).is_file() for src in REQUIRED_SCRIPTS)

favicon = next(link for link in parser.links if link.get("rel") == "icon")
href = favicon["href"]
assert href == "img/favicon-polonia.png", href
assert (ROOT / "docs" / href).is_file()

for key, value in parser.meta.items():
    if key == "og:image":
        assert not value.startswith(("http://", "https://")), value

print("site metadata: PASS")
