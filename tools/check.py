"""mkn.github.io: every internal link in _site/ reaches a file, and its #anchor an id there.

    python3 tools/check.py [--site _site]
"""

import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = set(), []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append(attrs[key])


def parse(path):
    p = Page()
    p.feed(path.read_text())
    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--site", default=str(ROOT / "_site"))
    site = Path(parser.parse_args().site).resolve()

    pages = {path: parse(path) for path in site.rglob("*.html")}
    errors = []
    for path, p in pages.items():
        for link in p.links:
            url = urlparse(link)
            if url.scheme or link.startswith("//"):
                continue  # external
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.exists():
                errors.append(f"{path.relative_to(site)}: {link}: no {target.relative_to(site) if site in target.parents else target}")
                continue
            if url.fragment and target.suffix == ".html":
                if url.fragment not in pages[target].ids:
                    errors.append(f"{path.relative_to(site)}: {link}: no #{url.fragment}")
    for e in errors:
        print(e)
    print(f"{len(pages)} pages, {sum(len(p.links) for p in pages.values())} links, {len(errors)} broken")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
