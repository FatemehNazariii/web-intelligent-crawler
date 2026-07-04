import re
import trafilatura
from bs4 import BeautifulSoup

BAD_SECTIONS = [
    "See also", "References", "External links", "Further reading",
    "Bibliography", "Notes", "Citations", "Sources", "Category",
    "Privacy policy", "Terms of use", "Cookie policy"
]

def extract_clean_text(html):
    if not html:
        return ""

    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        include_links=False
    )

    if not text or len(text) < 400:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()

        text = soup.get_text(separator=" ")

    text = re.sub(r"\s+", " ", text or "")

    for section in BAD_SECTIONS:
        if section in text:
            text = text.split(section)[0]

    return text.strip()