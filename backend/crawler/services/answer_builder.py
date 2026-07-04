from .ai_summarizer import summarize_ai


def build_final_answer(topic, context):

    if not context:
        return "No data found."

    prompt = f"""
You are a research assistant.

Topic: {topic}

Use the following information:

{context}

Write a structured answer:

1. Overview
2. Key Concepts
3. Important Facts
4. Conclusion

Make it natural, clear, and not copy-paste.
"""

    return summarize_ai(prompt, max_length=280, min_length=120)