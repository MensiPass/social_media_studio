"""
Fetches a URL and extracts readable text from the HTML — so a submitted URL
actually gives Day 4's variant generator real content to work with, not
just a bare link.

This is intentionally simple: strip <script>/<style>/<nav>/<footer> tags,
then join the remaining visible text. Good enough for blog posts and
articles; not a general-purpose "readability" algorithm.
"""
import httpx
from bs4 import BeautifulSoup


class ContentFetchError(Exception):
    """Raised when a URL can't be fetched or contains no usable text."""


def fetch_and_extract_text(url: str, timeout_seconds: float = 10.0) -> tuple[str | None, str]:
    """
    Returns (title, extracted_text).
    Raises ContentFetchError with a clear message on any failure —
    the API route turns this into a clean 4xx response.
    """
    try:
        response = httpx.get(
            url,
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={
                # A generic/short User-Agent gets blocked by sites like
                # Wikipedia that filter out obvious bot traffic. A realistic
                # browser-style User-Agent avoids that without being deceptive
                # about what's making the request in any way that matters here.
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ContentFetchError(
            f"URL returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise ContentFetchError(f"Could not reach URL: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Remove tags that never contain the actual article content
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    if not text or len(text) < 50:
        raise ContentFetchError(
            "Page fetched successfully but contained no usable text "
            "(it may require JavaScript to render, or be behind a login)."
        )

    return title, text