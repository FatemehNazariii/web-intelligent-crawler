from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from crawler.services.llm_service import chat_with_ollama
from crawler.services.storage_service import get_chunks


def retrieve_relevant_chunks(
    conversation_id: str,
    question: str,
    top_k: int = 4
) -> list[dict]:
    """
    بازیابی مرتبط‌ترین chunkها با TF-IDF.
    """

    chunks = get_chunks(conversation_id)

    if not chunks:
        return []

    chunk_texts = [
        chunk["chunk_text"]
        for chunk in chunks
    ]

    documents = chunk_texts + [question]

    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=15000
        )

        matrix = vectorizer.fit_transform(documents)

    except ValueError:
        return []

    question_vector = matrix[-1]
    chunk_vectors = matrix[:-1]

    similarities = cosine_similarity(
        question_vector,
        chunk_vectors
    ).flatten()

    ranked_indices = similarities.argsort()[::-1]

    results = []

    for index in ranked_indices[:top_k]:
        chunk = chunks[index].copy()
        chunk["score"] = float(similarities[index])
        results.append(chunk)

    return results


def answer_question(
    conversation_id: str,
    question: str,
    language: str = "fa",
    top_k: int = 4
) -> dict:
    """
    پاسخ‌گویی منبع‌محور با Ollama.
    """

    relevant_chunks = retrieve_relevant_chunks(
        conversation_id=conversation_id,
        question=question,
        top_k=top_k
    )

    if not relevant_chunks:
        return {
            "answer": (
                "هنوز منبعی برای این گفتگو ذخیره نشده است."
                if language == "fa"
                else "No sources have been stored for this conversation."
            ),
            "sources": [],
        }

    context_parts = []
    sources = []
    seen_urls = set()

    for index, chunk in enumerate(relevant_chunks, start=1):
        context_parts.append(
            f"""
[Source {index}]
Title: {chunk.get("title", "Untitled")}
URL: {chunk.get("url", "")}
Text:
{chunk.get("chunk_text", "")}
"""
        )

        url = chunk.get("url")

        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append(url)

    context = "\n".join(context_parts)

    if language == "fa":
        system_prompt = """
شما یک دستیار پژوهشی فارسی‌زبان هستید.

فقط بر اساس متن منابع داده‌شده به سؤال پاسخ بده.
حتی اگر منابع انگلیسی هستند، پاسخ نهایی باید کاملاً فارسی باشد.
هیچ اطلاعاتی خارج از منابع اضافه نکن.
اگر پاسخ در منابع وجود ندارد، صریحاً اعلام کن.
پاسخ را روان، دقیق و ساختارمند بنویس.
در پایان به شماره منابع مرتبط اشاره کن.
"""
    else:
        system_prompt = """
You are a source-grounded research assistant.

Answer only from the supplied source excerpts.
Do not add unsupported information.
If the answer is absent, say so clearly.
Cite the relevant source numbers in the response.
"""

    user_prompt = f"""
Question:
{question}

Source excerpts:
{context}
"""

    answer = chat_with_ollama(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.1
    )

    if not answer:
        answer = (
            "در پردازش پاسخ توسط مدل محلی خطایی رخ داد."
            if language == "fa"
            else "The local model could not generate an answer."
        )

    return {
        "answer": answer,
        "sources": sources,
    }