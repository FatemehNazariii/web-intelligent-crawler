import requests

BAD_MARKERS = [
    "too many requests",
    "access denied",
    "forbidden",
    "cloudflare",
    "wikimedia error",
    "captcha",
]

def fetch_page(url):
    try:
        response = requests.get(
            url,
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        if response.status_code != 200:
            return None

        html = response.text

        if any(marker in html.lower() for marker in BAD_MARKERS):
            return None

        return html

    except Exception:
        return None