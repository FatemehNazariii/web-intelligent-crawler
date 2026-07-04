import requests
from bs4 import BeautifulSoup

from search.seed_generator import get_seed_urls
from processing.extractor import extract_text
from processing.summarizer import summarize
from report.report_generator import generate_report


def extract_wiki_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if not href.startswith("/wiki/"):
            continue

        if ":" in href:
            continue

        if href == "/wiki/Main_Page":
            continue

        links.add("https://en.wikipedia.org" + href)

    return list(links)


def run(topic):
    base_urls = get_seed_urls(topic)

    visited = set()
    results = []

    print("\n🔎 Seed URLs:")
    for url in base_urls:
        print(" -", url)

    print("\n🔗 BFS Crawling...")

    queue = list(base_urls)
    depth = 0
    MAX_DEPTH = 2

    while queue and depth <= MAX_DEPTH:
        next_queue = []

        for url in queue:
            if url in visited:
                continue

            visited.add(url)

            try:
                response = requests.get(
                    url,
                    timeout=10,
                    headers={"User-Agent": "Mozilla/5.0"}
                )

                links = extract_wiki_links(response.text)

                for link in links[:20]:
                    if link not in visited:
                        next_queue.append(link)

            except Exception as e:
                print("⚠️ Crawl error:", e)

        queue = next_queue
        depth += 1

    urls = list(visited)[:15]

    print(f"\n📦 Total URLs to crawl: {len(urls)}")

    for url in urls:
        try:
            print(f"\n📥 Fetching: {url}")

            response = requests.get(
                url,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            print("HTML size:", len(response.text))

            text = extract_text(response.text)

            print("Extracted text length:", len(text) if text else 0)

            if not text or len(text) < 80:
                print("⚠️ Skipped (low quality content)")
                continue

            summary = summarize(text)

            results.append({
                "url": url,
                "summary": summary
            })

        except Exception as e:
            print("❌ Error:", e)

    print("\n====================")
    print("RESULTS COUNT:", len(results))
    print("====================\n")

    if not results:
        print("⚠️ No valid content extracted.")
        return

    generate_report(results, topic)


if __name__ == "__main__":
    topic = input("Enter topic: ")
    run(topic)