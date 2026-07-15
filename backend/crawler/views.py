import json
import time
import traceback
from uuid import uuid4

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# ============================================================
# ایمپورت سرویس‌های مورد نیاز
# ============================================================
from crawler.services.research_service import run_research


def json_response(data: dict, status: int = 200) -> JsonResponse:
    """
    ساخت پاسخ JSON با پشتیبانی صحیح از UTF-8.
    """
    response = JsonResponse(
        data,
        status=status,
        json_dumps_params={"ensure_ascii": False}
    )
    response["Content-Type"] = "application/json; charset=utf-8"
    return response


# ============================================================
# API چت پژوهشی (موجود)
# ============================================================
@csrf_exempt
@require_POST
def chat_api(request):
    """
    API اصلی چت پژوهشی.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return json_response(
            {"error": "بدنه درخواست باید JSON معتبر باشد."},
            status=400
        )

    message = str(data.get("message", "")).strip()
    conversation_id = str(data.get("conversation_id") or uuid4()).strip()

    if not message:
        return json_response(
            {"error": "پیام کاربر نمی‌تواند خالی باشد."},
            status=400
        )

    try:
        # توجه: تابع handle_chat_message باید تعریف یا ایمپورت شود
        result = handle_chat_message(
            message=message,
            conversation_id=conversation_id
        )

        if not isinstance(result, dict):
            return json_response(
                {
                    "error": "خروجی سرویس چت معتبر نیست.",
                    "details": f"Expected dict, got {type(result).__name__}"
                },
                status=500
            )

        return json_response(result, status=200)

    except Exception as error:
        traceback.print_exc()
        print(f"[Chat API Error] {type(error).__name__}: {error}")
        return json_response(
            {
                "error": "در پردازش درخواست خطایی رخ داد.",
                "details": str(error)
            },
            status=500
        )


# ============================================================
# API پژوهش (جدید)
# ============================================================
@csrf_exempt
@require_POST
def research_api(request):
    """
    API مخصوص پژوهش.
    دریافت موضوع، اجرای پژوهش و بازگرداندن گزارش کامل.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return json_response(
            {"error": "بدنه درخواست باید JSON معتبر باشد."},
            status=400
        )

    topic = data.get("topic", "").strip()
    language = data.get("language", "fa")
    max_sources = data.get("max_sources", 3)

    if not topic:
        return json_response(
            {"error": "موضوع پژوهش نمی‌تواند خالی باشد."},
            status=400
        )

    try:
        # تولید conversation_id یکتا برای هر پژوهش
        conversation_id = f"research-{int(time.time())}-{uuid4().hex[:8]}"

        result = run_research(
            conversation_id=conversation_id,
            topic=topic,
            language=language,
            max_sources=max_sources
        )

        return json_response(result, status=200)

    except Exception as error:
        traceback.print_exc()
        print(f"[Research API Error] {type(error).__name__}: {error}")
        return json_response(
            {
                "error": "خطا در اجرای پژوهش",
                "details": str(error)
            },
            status=500
        )
        
@csrf_exempt
@require_POST
def translate_api(request):
    """
    ترجمه یک متن به زبان مقصد (فارسی یا انگلیسی) با استفاده از Ollama
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return json_response({"error": "Invalid JSON"}, status=400)

    text = data.get("text", "").strip()
    target_language = data.get("target_language", "fa")  # 'fa' یا 'en'

    if not text:
        return json_response({"error": "Text is required"}, status=400)

    try:
        from crawler.services.llm_service import chat_with_ollama

        if target_language == "fa":
            system_prompt = """
شما یک مترجم حرفه‌ای هستید.
متن زیر را به فارسی روان و طبیعی ترجمه کنید.
فقط متن ترجمه‌شده را خروجی بدهید، بدون توضیح اضافی.
"""
        else:
            system_prompt = """
You are a professional translator.
Translate the following text to natural English.
Output only the translated text, no extra explanation.
"""

        user_prompt = f"Text to translate:\n\n{text}"

        result = chat_with_ollama(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            num_predict=len(text.split()) * 3 + 100,  # تخمین تعداد توکن‌های مورد نیاز
            model="gemma2:9b"  # یا مدل دلخواه
        )

        if not result:
            return json_response({"error": "Translation failed"}, status=500)

        return json_response({"translated_text": result}, status=200)

    except Exception as error:
        traceback.print_exc()
        return json_response({"error": str(error)}, status=500)
        
@csrf_exempt
@require_POST
def qa_api(request):
    """
    API پرسش و پاسخ بر اساس محتوای خزش‌شده
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return json_response({"error": "Invalid JSON"}, status=400)

    conversation_id = data.get("conversation_id", "").strip()
    question = data.get("question", "").strip()
    language = data.get("language", "fa")
    top_k = data.get("top_k", 4)

    if not conversation_id:
        return json_response({"error": "conversation_id is required"}, status=400)

    if not question:
        return json_response({"error": "Question is required"}, status=400)

    try:
        from crawler.services.qa_service import answer_question

        result = answer_question(
            conversation_id=conversation_id,
            question=question,
            language=language,
            top_k=top_k
        )

        return json_response(result, status=200)

    except Exception as error:
        traceback.print_exc()
        return json_response({"error": str(error)}, status=500)