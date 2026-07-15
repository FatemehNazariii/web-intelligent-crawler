from bs4 import BeautifulSoup
import trafilatura


def extract_title(html: str) -> str:
    """
    استخراج عنوان صفحه از HTML.
    """

    if not html:
        return "بدون عنوان"

    soup = BeautifulSoup(html, "html.parser")

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    h1 = soup.find("h1")

    if h1:
        return h1.get_text(" ", strip=True)

    return "بدون عنوان"


def extract_main_text(
    html: str,
    url: str | None = None
) -> str | None:
    """
    استخراج متن اصلی صفحه.
    ابتدا Trafilatura و سپس BeautifulSoup استفاده می‌شود.
    """

    if not html:
        return None

    try:
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )

        if extracted and len(extracted.strip()) >= 200:
            return extracted.strip()

    except Exception as error:
        print(f"[Extractor][Trafilatura] {url or ''}: {error}")

    try:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form",
            "noscript",
            "svg",
        ]):
            tag.decompose()

        main_element = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id="content")
            or soup.body
            or soup
        )

        text = main_element.get_text(
            separator=" ",
            strip=True
        )

        if text and len(text.strip()) >= 200:
            return text.strip()

    except Exception as error:
        print(f"[Extractor][BeautifulSoup] {url or ''}: {error}")

    return None