"""MkDocs hook: make local service addresses clickable.

Inline code such as `http://127.0.0.1:8123/play` becomes a link, so a reader
with the profile running opens the UI in one click. Each link carries
rel="nofollow", which Google documents as the value for a link it should not
crawl from this site; a 127.0.0.1 address only exists on the reader's machine.
Code blocks are left alone, because their code element is not bare.
"""

import re

_LOCAL = re.compile(r"(?<!<pre>)<code>(http://127\.0\.0\.1[^<\s]*)</code>")


def link_local_addresses(html: str) -> str:
    """Wrap each inline-code local address in a nofollow link."""
    return _LOCAL.sub(r'<a href="\1" rel="nofollow"><code>\1</code></a>', html)


def on_page_content(html, page, config, files):
    return link_local_addresses(html)
