from urllib.parse import urlparse

from .answer_builder import build_final_answer
from .search_service import search_web
from .ranking_service import score_url
from .crawler_service import fetch_page
from .extractor_service import extract_clean_text
from .ai_summarizer import summarize_ai


def build_report(topic):

    # 1. SEARCH
    urls = search_web(topic, max_results=8)

    # حذف تکراری‌ها
    urls = list(dict.fromkeys(urls))

    # 2. RANKING
    urls = sorted(urls, key=score_url, reverse=True)

    results = []
    all_texts = []

    # 3. CRAWL + EXTRACT (NO AI HERE)
    for url in urls:

        html = fetch_page(url)
        if not html:
            continue

        text = extract_clean_text(html)
        if not text or len(text) < 500:
            continue

        domain = urlparse(url).netloc.replace("www.", "")

        results.append({
            "title": domain,
            "url": url,
            "text_length": len(text),
            "score": score_url(url),
        })

        all_texts.append(text)

        if len(results) < 3:
            urls = search_web(topic, max_results=15)

    # 4. HANDLE EMPTY CASE
    if not results:
        return {
            "topic": topic,
            "count": 0,
            "final_summary": "No valid sources found.",
            "results": []
        }

    # 5. FINAL AI STEP (IMPORTANT FIX)
    combined_text = " ".join(all_texts)

    final_summary = build_final_answer(topic, combined_text)

    # 6. RETURN CLEAN RESPONSE
    return {
        "topic": topic,
        "count": len(results),
        "final_summary": final_summary,
        "results": results
    }