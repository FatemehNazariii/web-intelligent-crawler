import re
from sklearn.feature_extraction.text import TfidfVectorizer

def summarize_text(text, top_n=4, max_chars=1000):
    if not text:
        return ""

    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 50]

    if not sentences:
        return text[:max_chars]

    if len(sentences) <= top_n:
        return " ".join(sentences)[:max_chars]

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(sentences)
        scores = matrix.sum(axis=1).A1

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        selected = sorted(ranked[:top_n], key=lambda x: x[0])

        summary = " ".join(sentences[i] for i, _ in selected)
        summary = re.sub(r"\s+", " ", summary)

        return summary[:max_chars]

    except Exception:
        return " ".join(sentences[:top_n])[:max_chars]