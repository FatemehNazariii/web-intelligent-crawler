from ddgs import DDGS
from urllib.parse import urlparse, quote


TRUSTED_DOMAINS = [
    "wikipedia.org",
    "britannica.com",
    "nasa.gov",
    "who.int",
    "un.org",
    "noaa.gov",
    "nature.com",
    "science.org",
    "ieee.org",
    "mit.edu",
    "stanford.edu",
    "harvard.edu",
    "nih.gov",
    "cdc.gov",
    "nationalgeographic.com",
    "bbc.com",
]

BLOCKED_KEYWORDS = [
    "youtube", "facebook", "instagram", "twitter", "x.com",
    "tiktok", "linkedin", "reddit", "pinterest",
    "buy", "shop", "rent", "price", "deal", "discount",
    "coupon", "sale", "store", "cart", "login",
    "car.com", "modelcar", "car-news", "used-cars",
]


def get_domain(url):
    return urlparse(url).netloc.lower().replace("www.", "")


def is_blocked(url):
    lowered = url.lower()
    return any(word in lowered for word in BLOCKED_KEYWORDS)


def score_url(url):
    domain = get_domain(url)
    score = 50

    for trusted in TRUSTED_DOMAINS:
        if trusted in domain:
            score += 60

    if ".edu" in domain:
        score += 40

    if ".gov" in domain:
        score += 40

    if is_blocked(url):
        score -= 100

    return score


def wikipedia_fallback(topic):
    return f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"


def britannica_fallback(topic):
    return f"https://www.britannica.com/search?query={quote(topic)}"


def search_web(topic, max_results=8):
    collected = {}

    queries = [
        f"{topic} site:wikipedia.org",
        f"{topic} site:britannica.com",
        f"{topic} explained",
        f"{topic} definition",
        f"{topic} overview",
        topic,
    ]

    try:
        with DDGS() as ddgs:
            for query in queries:
                results = ddgs.text(query, max_results=10)

                for item in results:
                    url = item.get("href") or item.get("url")

                    if not url:
                        continue

                    url = url.strip()

                    if not url.startswith("http"):
                        continue

                    if is_blocked(url):
                        continue

                    domain = get_domain(url)

                    if domain in collected:
                        continue

                    collected[domain] = {
                        "url": url,
                        "score": score_url(url),
                    }

    except Exception as e:
        print("Search error:", e)

    ranked = sorted(
        collected.values(),
        key=lambda item: item["score"],
        reverse=True
    )

    urls = [item["url"] for item in ranked]

    # fallback برای اینکه همیشه حداقل چند منبع پایه داشته باشیم
    fallback_urls = [
        wikipedia_fallback(topic),
    ]

    for fallback in fallback_urls:
        if fallback not in urls:
            urls.insert(0, fallback)

    return urls[:max_results]