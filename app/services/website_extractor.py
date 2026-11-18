import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, Comment
from app.config import settings
from app.utils.validators import resolve_and_check, validate_url, SSRFError

logger = logging.getLogger(__name__)


class WebsiteExtractor:
    """Fetches and extracts meaningful text content from a website URL."""

    MAX_REDIRECTS = 10

    def __init__(self):
        self.timeout = settings.REQUEST_TIMEOUT
        self.max_content = settings.MAX_CONTENT_LENGTH
        self.max_response_bytes = settings.MAX_RESPONSE_BYTES
        self.last_stats: dict = {}
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    @staticmethod
    def _family(address: str) -> int:
        parsed = ipaddress.ip_address(address.split("%", 1)[0])
        return socket.AF_INET6 if parsed.version == 6 else socket.AF_INET

    class _PinnedResolver(aiohttp.abc.AbstractResolver):
        """Resolve only to addresses already checked as public for this hop."""

        def __init__(self, hostname: str, addresses: list[str]):
            self.hostname = hostname.encode("idna").decode("ascii").lower().rstrip(".")
            self.addresses = addresses

        async def resolve(self, host: str, port: int = 0, family: int = socket.AF_UNSPEC):
            normalized = host.encode("idna").decode("ascii").lower().rstrip(".")
            if normalized != self.hostname:
                raise OSError("Unexpected hostname during pinned DNS resolution")
            records = []
            for address in self.addresses:
                clean_address = address.split("%", 1)[0]
                address_family = WebsiteExtractor._family(clean_address)
                if family not in (socket.AF_UNSPEC, address_family):
                    continue
                records.append({
                    "hostname": host,
                    "host": clean_address,
                    "port": port,
                    "family": address_family,
                    "proto": socket.IPPROTO_TCP,
                    "flags": socket.AI_NUMERICHOST,
                })
            if not records:
                raise OSError("No validated address is available for this hostname")
            return records

        async def close(self):
            return None

    async def _safe_get(self, url: str) -> str:
        """
        Fetch a URL with SSRF-safe redirect handling.

        Redirects are followed manually so that every hop's destination
        is re-resolved and validated against private IP ranges.  This
        closes the TOCTOU gap where the initial hostname passes validation
        but a redirect points to an internal address.

        Pins each connection to a validated DNS result and streams the page
        under the configured byte limit.
        """
        visited: set[str] = set()
        current_url = url

        for redirect_count in range(self.MAX_REDIRECTS + 1):
            if current_url in visited:
                raise ConnectionError("Redirect loop detected")
            visited.add(current_url)

            timeout = aiohttp.ClientTimeout(total=self.timeout, connect=min(self.timeout, 10), sock_read=self.timeout)

            try:
                parsed = urlparse(current_url)
                hostname = parsed.hostname
                if not hostname:
                    raise ConnectionError("URL or redirect has no hostname")
                # Validate scheme, credentials, port, and every DNS result.
                validated_url = validate_url(current_url)
                addresses = resolve_and_check(hostname)
                resolver = self._PinnedResolver(hostname, addresses)
                connector = aiohttp.TCPConnector(resolver=resolver, use_dns_cache=False)
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    trust_env=False,
                    headers=self.headers,
                ) as session:
                    async with session.get(validated_url, allow_redirects=False) as response:
                        if response.status in {301, 302, 303, 307, 308}:
                            location = response.headers.get("Location")
                            if not location or redirect_count >= self.MAX_REDIRECTS:
                                raise ConnectionError("The website redirect limit was reached")
                            current_url = urljoin(validated_url, location)
                            continue

                        if response.status >= 400:
                            raise ConnectionError(f"HTTP {response.status} error fetching website")
                        content_type = response.headers.get("Content-Type", "").lower()
                        if not any(kind in content_type for kind in ("text/html", "application/xhtml+xml")):
                            raise ConnectionError("The URL did not return an HTML page")
                        if response.content_length and response.content_length > self.max_response_bytes:
                            raise ConnectionError("Website response exceeds the configured size limit")

                        body = bytearray()
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            body.extend(chunk)
                            if len(body) > self.max_response_bytes:
                                raise ConnectionError("Website response exceeds the configured size limit")
                        encoding = response.charset or "utf-8"
                        try:
                            return bytes(body).decode(encoding, errors="replace")
                        except LookupError:
                            return bytes(body).decode("utf-8", errors="replace")
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError, UnicodeError) as exc:
                if isinstance(exc, ConnectionError):
                    raise
                raise ConnectionError("Could not safely fetch the website") from exc
            except (SSRFError, ValueError) as exc:
                raise ConnectionError(f"Website URL blocked or invalid: {exc}") from exc

        raise ConnectionError(f"Too many redirects (>{self.MAX_REDIRECTS})")

    async def fetch_html(self, url: str) -> str:
        """Fetch raw HTML from the URL with SSRF-safe redirect handling."""
        return await self._safe_get(url)

    def extract_content(self, html: str) -> dict:
        """
        Parse HTML and extract structured website content.

        Returns a dict with keys:
            title, meta_description, meta_keywords, headings,
            main_text, navigation_links, image_alt_texts
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove noise elements
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # Title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Meta tags
        meta_desc = ""
        meta_kw = ""
        for meta in soup.find_all("meta"):
            name = (meta.get("name") or meta.get("property") or "").lower()
            content = meta.get("content", "").strip()
            if name in ("description", "og:description"):
                meta_desc = meta_desc or content
            elif name == "keywords":
                meta_kw = content

        # Headings
        headings = []
        for level in range(1, 7):
            for h in soup.find_all(f"h{level}"):
                text = h.get_text(strip=True)
                if text:
                    headings.append({"level": level, "text": text})

        # Main text – prefer <main> or <article>, fall back to <body>
        main_el = soup.find("main") or soup.find("article") or soup.find("body")
        paragraphs = []
        if main_el:
            for p in main_el.find_all(["p", "li", "span", "div"], recursive=True):
                text = p.get_text(separator=" ", strip=True)
                if text and len(text) > 20:
                    paragraphs.append(text)

        # De-duplicate identical paragraphs
        deduped = []
        seen = set()
        for p in paragraphs:
            if p not in seen:
                deduped.append(p)
                seen.add(p)

        main_text = "\n".join(deduped)

        # Truncate to stay within token budget
        if len(main_text) > self.max_content:
            main_text = main_text[: self.max_content] + "\n[Content truncated]"

        # Navigation / internal links
        nav_links = []
        for a in soup.find_all("a", href=True):
            link_text = a.get_text(strip=True)
            if link_text and len(link_text) < 100:
                nav_links.append(link_text)
        nav_links = list(dict.fromkeys(nav_links))[:50]  # top 50 unique

        # Image alt texts (useful for understanding services)
        alt_texts = []
        for img in soup.find_all("img", alt=True):
            alt = img["alt"].strip()
            if alt and alt.lower() not in ("logo", "image", "icon", ""):
                alt_texts.append(alt)
        alt_texts = list(dict.fromkeys(alt_texts))[:30]

        return {
            "title": title,
            "meta_description": meta_desc,
            "meta_keywords": meta_kw,
            "headings": headings,
            "main_text": main_text,
            "navigation_links": nav_links,
            "image_alt_texts": alt_texts,
        }

    async def extract(self, url: str) -> dict:
        """Full pipeline: fetch -> parse -> extract."""
        logger.info("Fetching website: %s", url)
        html = await self.fetch_html(url)
        logger.info("Extracting content from: %s", url)
        content = self.extract_content(html)
        content["url"] = url
        self.last_stats = {
            "raw_bytes": len(html.encode("utf-8")),
            "raw_chars": len(html),
            "cleaned_chars": len(content.get("main_text", "")),
        }
        return content
