from urllib.parse import urlparse

TRUSTED_DOMAINS = {
    "wikipedia.org": 100,
    "britannica.com": 95,
    "nih.gov": 95,
    "nasa.gov": 95,
    "who.int": 95,
    "nature.com": 95,
    "ieee.org": 90,
    "mit.edu": 90,
    "stanford.edu": 90,
    "harvard.edu": 90,
    "microsoft.com": 85,
    "ibm.com": 85,
}

BAD_WORDS = [
    "buy", "shop", "rent", "price", "deal", "discount",
    "coupon", "sale", "login", "signup", "cart"
]

def score_url(url):
    domain = urlparse(url).netloc.lower()
    score = 50

    for trusted, value in TRUSTED_DOMAINS.items():
        if trusted in domain:
            score = value

    lowered = url.lower()
    for word in BAD_WORDS:
        if word in lowered:
            score -= 35

    return score