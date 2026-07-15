from __future__ import annotations

import re
from typing import Any
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

from hazm import Normalizer

try:
    import wordninja
except ImportError:
    wordninja = None

from crawler.services.search_service import search_web
from crawler.services.crawler_service import fetch_page
from crawler.services.extractor_service import (
    extract_title,
    extract_main_text,
)
from crawler.services.llm_service import chat_with_ollama, OLLAMA_MODEL
from crawler.services.storage_service import (
    clear_research_data,
    save_source,
    save_chunk,
    update_conversation,
)

# ============================================================
# تنظیمات ثابت
# ============================================================

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}

MAX_ALLOWED_SOURCES = 10
MIN_SOURCE_TEXT_LENGTH = 300

SUMMARY_INPUT_LIMIT = 6500
SUMMARY_NUM_PREDICT = 1000           # کاهش برای سرعت
REPORT_NUM_PREDICT = 4096             # کاهش از ۸۱۹۲ برای مدیریت زمان

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 150

SECTION_MAX_ATTEMPTS = 2              # کاهش تلاش‌های مجدد

PERSIAN_MODELS = ["gemma2:9b"]         # مدل اصلی برای فارسی و انگلیسی

PERSIAN_NORMALIZER = Normalizer(
    correct_spacing=True,
    remove_diacritics=True,
    remove_specials_chars=False,
    decrease_repeated_chars=False,
    persian_style=True,
    persian_numbers=False,
    unicodes_replacement=True,
    seperate_mi=True,
)


# ============================================================
# توابع کمکی
# ============================================================

def clean_extracted_text(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\[\s*\d+\s*\]", " ", text)
    text = re.sub(r"\[\s*edit\s*\]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_persian_text(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    normalized_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            normalized_lines.append("")
            continue
        if line.startswith("#"):
            match = re.match(r"^(#+)\s*(.*)$", line)
            if match:
                hashes = match.group(1)
                heading_text = match.group(2)
                if heading_text:
                    heading_text = PERSIAN_NORMALIZER.normalize(heading_text)
                normalized_lines.append(f"{hashes} {heading_text}".rstrip())
                continue
        if "http://" in line or "https://" in line:
            normalized_lines.append(line)
            continue
        line = PERSIAN_NORMALIZER.normalize(line)
        line = re.sub(r"\s+([،؛:,.!?؟])", r"\1", line)
        line = re.sub(r"([،؛:!?؟])(?=[^\s\n])", r"\1 ", line)
        line = re.sub(r"\bمی\s+([آ-ی]+)", r"می‌\1", line)
        line = re.sub(r"\bنمی\s+([آ-ی]+)", r"نمی‌\1", line)
        line = re.sub(r"[ \t]{2,}", " ", line)
        normalized_lines.append(line.strip())
    normalized_text = "\n".join(normalized_lines)
    normalized_text = re.sub(r"\n{3,}", "\n\n", normalized_text)
    return normalized_text.strip()


def normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return ""
    scheme = parts.scheme.lower() if parts.scheme else "https"
    if scheme not in {"http", "https"}:
        return ""
    hostname = (parts.hostname or "").lower()
    if not hostname:
        return ""
    try:
        port = parts.port
    except ValueError:
        port = None
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    path = path.rstrip("/") or "/"
    if hostname.endswith("wikipedia.org"):
        path = path.lower()
    filtered_query: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower.startswith("utm_"):
            continue
        if key_lower in TRACKING_QUERY_KEYS:
            continue
        filtered_query.append((key, value))
    query = urlencode(sorted(filtered_query))
    return urlunsplit((scheme, netloc, path, query, ""))


def get_domain_group(url: str) -> str:
    if not url:
        return ""
    try:
        hostname = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""
    if hostname.startswith("www."):
        hostname = hostname[4:]
    if not hostname:
        return ""
    known_domain_groups = {
        "wikipedia.org": "wikipedia.org",
        "britannica.com": "britannica.com",
        "nasa.gov": "nasa.gov",
        "ibm.com": "ibm.com",
        "amazon.com": "amazon.com",
        "coursera.org": "coursera.org",
        "academia.edu": "academia.edu",
        "medium.com": "medium.com",
        "google.com": "google.com",
        "microsoft.com": "microsoft.com",
        "bbc.co.uk": "bbc.co.uk",
    }
    for suffix, group in known_domain_groups.items():
        if hostname == suffix or hostname.endswith(f".{suffix}"):
            return group
    parts = hostname.split(".")
    compound_tlds = {
        "co.uk", "org.uk", "ac.uk", "gov.uk",
        "com.au", "net.au", "org.au", "co.jp"
    }
    if len(parts) >= 3:
        last_two = ".".join(parts[-2:])
        if last_two in compound_tlds:
            return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return hostname


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    chunks: list[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length:
            boundaries = [
                text.rfind(". ", start, end),
                text.rfind("؟", start, end),
                text.rfind("! ", start, end),
                text.rfind("\n", start, end),
            ]
            best_boundary = max(boundaries)
            minimum_boundary = start + chunk_size // 2
            if best_boundary > minimum_boundary:
                end = best_boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def summarize_with_ollama(text: str, language: str, topic: str) -> str:
    all_chunks = chunk_text(text, chunk_size=1200, overlap=100)
    if all_chunks:
        selected_chunks = [all_chunks[0]]
        if len(all_chunks) > 2:
            selected_chunks.append(all_chunks[len(all_chunks) // 2])
        if len(all_chunks) > 1:
            selected_chunks.append(all_chunks[-1])
        prompt_text = "\n\n---\n\n".join(selected_chunks)
    else:
        prompt_text = text[:SUMMARY_INPUT_LIMIT]

    # ✅ استفاده از gemma2:9b برای هر دو زبان
    model_to_use = "gemma2:9b"

    if language == "fa":
        system_prompt = f"""
شما یک خلاصه‌ساز پژوهشی حرفه‌ای فارسی‌زبان هستید.

متن ارائه‌شده را فقط با تمرکز بر موضوع «{topic}» خلاصه کن.

قواعد الزامی:

- خروجی فقط به زبان فارسی باشد.
- فقط از اطلاعات صریح موجود در متن استفاده کن.
- هیچ اطلاعات، ادعا، مثال یا نتیجه‌ای از خودت اضافه نکن.
- عددها، تاریخ‌ها و نام‌ها را تغییر نده.
- اگر عدد، تاریخ یا نامی نامطمئن است، آن را حذف کن.
- از ترجمه تحت‌اللفظی خودداری کن.
- متن فارسی طبیعی، روان و از نظر دستوری صحیح باشد.
- جمله ناقص، تکراری، مبهم یا متناقض ننویس.
- تعریف موضوع، یافته‌های اصلی، کاربردها و چالش‌ها را پوشش بده.
- فقط درباره مطالب مرتبط با موضوع اصلی بنویس.
- خلاصه حدود ۱۵۰ تا ۲۵۰ کلمه باشد.
- عنوان، فهرست منابع، نسخه انگلیسی یا روند فکر کردن ننویس.
- virtual assistant را «دستیار مجازی» ترجمه کن.
- self-driving car را «خودروی خودران» ترجمه کن.
- generative AI را «هوش مصنوعی مولد» ترجمه کن.
- deep neural network را «شبکه عصبی عمیق» ترجمه کن.
- از فعل‌های «می‌باشد» و «می‌باشند» استفاده نکن.
- در اولین استفاده بنویس "هوش مصنوعی (AI)" و بعد فقط "هوش مصنوعی" استفاده کن.
"""
    else:
        system_prompt = f"""
You are a source-grounded research summarizer.

Summarize the supplied source text only as it relates to:
"{topic}"

Rules:

- Write only in English.
- Use only explicit information from the supplied source.
- Do not add unsupported claims, examples, or conclusions.
- Preserve names, dates, and numbers accurately.
- Remove uncertain facts instead of guessing.
- Avoid repetition, ambiguity, and incomplete sentences.
- Cover relevant definitions, findings, applications, and challenges.
- Produce a coherent summary of approximately 150 to 250 words.
- Do not include headings, source lists, translations, or reasoning.
"""

    result = chat_with_ollama(
        system_prompt=system_prompt,
        user_prompt=prompt_text,
        temperature=0.05,
        num_predict=SUMMARY_NUM_PREDICT,
        num_ctx=16384,
        model=model_to_use,
    )

    if result:
        result = result.strip()
        if language == "fa":
            result = normalize_persian_text(result)
        return result

    fallback = prompt_text[:1000].strip()
    if language == "fa":
        fallback = normalize_persian_text(fallback)
    return fallback


def format_sources(processed_sources: list[dict[str, Any]], language: str) -> str:
    heading = "## منابع" if language == "fa" else "## References"
    lines = [heading]
    for index, source in enumerate(processed_sources, start=1):
        title = str(source.get("title") or "بدون عنوان").strip()
        url = str(source.get("url") or "").strip()
        lines.append(f"{index}. {title} — {url}")
    return "\n".join(lines)


def fix_english_spacing(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([a-z])([,.!?;:])(?!\s|$)", r"\1\2 ", text)
    text = re.sub(r"([,.!?;:])([A-Za-z])", r"\1 \2", text)
    text = re.sub(r"([a-z])([0-9])", r"\1 \2", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def fix_spacing(text: str) -> str:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([a-z])([0-9])", r"\1 \2", text)
    text = re.sub(r"([.!?,])([A-Za-z])", r"\1 \2", text)
    return text


def repair_glued_words(text: str) -> str:
    if not text or wordninja is None:
        return text

    def _fix_token(match: re.Match) -> str:
        token = match.group(0)
        parts = wordninja.split(token)
        if len(parts) <= 1:
            return token
        if any(len(part) < 2 for part in parts):
            return token
        rebuilt = " ".join(parts)
        if token[0].isupper():
            rebuilt = rebuilt[0].upper() + rebuilt[1:]
        return rebuilt

    return re.sub(r"[A-Za-z]{10,}", _fix_token, text)


def repair_english_text(text: str) -> str:
    if not text:
        return text
    text = fix_english_spacing(text)
    text = repair_glued_words(text)
    return text


def polish_section(text: str, language: str) -> str:
    """پالایش ساده متن برای بهبود کیفیت نگارشی (فقط برای فارسی)"""
    if language != "fa" or not text:
        return text

    # حذف جملات تکراری
    sentences = text.split('. ')
    unique_sentences = []
    for s in sentences:
        if s not in unique_sentences:
            unique_sentences.append(s)
    text = '. '.join(unique_sentences)

    # اصلاح فاصله‌ها
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([،؛:.!؟])', r'\1', text)
    text = re.sub(r'([،؛:.!؟])(?=[^\s])', r'\1 ', text)

    # اصلاح نیم‌فاصله
    text = re.sub(r'(می|نمی)\s+', r'\1‌', text)

    return text.strip()


# ============================================================
# اعتبارسنجی بخش‌ها
# ============================================================

def get_section_validation_rules(language: str, section_name: str) -> dict[str, Any]:
    rules = {
        "min_words": 30,
        "max_words": None,
        "required_groups": [],
        "forbidden_words": [],
    }

    if language == "en":
        if section_name == "introduction":
            rules["required_groups"] = [
                [r'\bdefin(e|ition|es)?\b', r'\brefers to\b', r'\bwhat is\b'],
                [r'\bhist(ory|orical)?\b', r'\borigins?\b', r'\bearly\b', r'\bmid-20th\b']
            ]
            rules["forbidden_words"] = [
                r'\bapplication(s)?\b', r'\bcompany\b', r'\bbenefit(s)?\b',
                r'\brisk\b', r'\bchallenge(s)?\b', r'\bexample\b'
            ]
            rules["max_words"] = 400
        elif section_name == "findings":
            rules["required_groups"] = [
                [r'\bfinding(s)?\b', r'\bresearch\b', r'\bresult(s)?\b']
            ]
            rules["forbidden_words"] = [r'\bdefinition\b', r'\bintroduction\b']
        elif section_name == "applications":
            rules["required_groups"] = [
                [r'\bapplication(s)?\b', r'\buse(s)?\b'],
                [r'\bbenefit(s)?\b', r'\badvantage(s)?\b', r'\bimprove\b']
            ]
            rules["forbidden_words"] = [r'\bdefinition\b']
        elif section_name == "challenges":
            rules["required_groups"] = [
                [r'\bchallenge(s)?\b', r'\blimitation(s)?\b', r'\bdifficult(y|ies)\b']
            ]
        elif section_name == "conclusion":
            rules["min_words"] = 20
            rules["max_words"] = 350
            rules["forbidden_words"] = [
                r'\bexample\b', r'\bcompany\b', r'\bTuring\b', r'\bNLP\b',
                r'\brobotics\b', r'\bapplication(s)?\b', r'\bbenefit(s)?\b',
                r'\bweb search\b', r'\bchatbots?\b', r'\bautonomous vehicles?\b',
                r'\bgenerative AI\b', r'\bimage\b', r'\bvideo\b',
                r'\bstate space search\b', r'\bformal logic\b', r'\bneural networks\b',
                r'\bstatistical methods\b', r'\bkey techniques\b'
            ]
            rules["required_groups"] = []

    else:  # fa
        if section_name == "introduction":
            rules["required_groups"] = [
                [r'\bتعریف\b', r'\bبه\s*(\bچه\b)?\s*(\bچیست\b)?\b'],
                [r'\bتاریخ\b', r'\bپیشینه\b', r'\bسابقه\b', r'\bاولین\b', r'\bدهه\s*((۱۹)?[۵۵۰۰]|۵۰)\b', r'\bسال\s*۱۹۵۰\b']
            ]
            rules["forbidden_words"] = [
                r'\bکاربرد\b', r'\bشرکت\b', r'\bمزیت\b',
                r'\bخطر\b', r'\bچالش\b', r'\bمثال\b'
            ]
            rules["max_words"] = 500
        elif section_name == "findings":
            rules["required_groups"] = [
                [r'\bیافته\b', r'\bپژوهش\b', r'\bنتایج\b']
            ]
            rules["forbidden_words"] = [r'\bتعریف\b']
        elif section_name == "applications":
            rules["required_groups"] = [
                [r'\bکاربرد\b', r'\bاستفاده\b'],
                [r'\bمزیت\b', r'\bسود\b', r'\bبهبود\b']
            ]
            rules["forbidden_words"] = [r'\bتعریف\b']
        elif section_name == "challenges":
            rules["required_groups"] = [
                [r'\bچالش\b', r'\bمحدودیت\b', r'\bمشکل\b']
            ]
        elif section_name == "conclusion":
            rules["min_words"] = 20
            rules["max_words"] = 350
            rules["forbidden_words"] = [
                r'\bشرکت\b', r'\bتورینگ\b',
                r'\bرباتیک\b', r'\bکاربرد\b', r'\bمزیت\b',
                r'\bجستجوی وب\b', r'\bچت‌بات\b', r'\bخودروی خودران\b',
                r'\bهوش مصنوعی مولد\b', r'\bتصویر\b', r'\bویدئو\b'
            ]
            rules["required_groups"] = []

    return rules


def validate_section(section_name: str, text: str, language: str) -> tuple[bool, str]:
    if not text:
        return False, "empty text"

    words = text.split()
    word_count = len(words)

    rules = get_section_validation_rules(language, section_name)

    min_words = rules.get("min_words", 30)
    if word_count < min_words:
        return False, f"text too short ({word_count} words, min {min_words})"

    max_words = rules.get("max_words")
    if max_words and word_count > max_words:
        return False, f"text too long ({word_count} words, max {max_words})"

    # ✅ فقط برای فارسی تعداد پاراگراف‌ها را بررسی می‌کنیم
    if language == "fa":
        paragraphs = text.split('\n\n')
        if len(paragraphs) < 2:
            return False, "not enough paragraphs"

    forbidden = rules.get("forbidden_words", [])
    text_lower = text.lower()
    for pattern in forbidden:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return False, f"contains forbidden word/phrase: {pattern}"

    required_groups = rules.get("required_groups", [])
    for group in required_groups:
        found = any(re.search(p, text_lower, re.IGNORECASE) for p in group)
        if not found:
            return False, f"missing required word/phrase from group: {group}"

    return True, ""


def postprocess_conclusion(text: str) -> str:
    forbidden_patterns = [
        r'\bapplication(s)?\b', r'\bcompany\b', r'\bbenefit(s)?\b',
        r'\bweb search\b', r'\bchatbots?\b', r'\bautonomous vehicles?\b',
        r'\bgenerative AI\b', r'\bimage\b', r'\bvideo\b',
        r'\bstate space search\b', r'\bformal logic\b', r'\bneural networks\b',
        r'\bstatistical methods\b', r'\bkey techniques\b', r'\bTuring\b',
        r'\bNLP\b', r'\brobotics\b'
    ]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    filtered = [s for s in sentences if not any(re.search(p, s, re.IGNORECASE) for p in forbidden_patterns)]
    if not filtered:
        return text
    return ' '.join(filtered).strip()


# ============================================================
# تولید بخش
# ============================================================

def generate_section(
    section_name: str,
    topic: str,
    language: str,
    context: str,
) -> str:

    if language == "fa":
        context = fix_spacing(context)
        num_predict = REPORT_NUM_PREDICT   # 4096
        num_ctx = 16384
        temperature = 0.3
        models_to_try = PERSIAN_MODELS     # ["gemma2:9b"]
    else:
        context = fix_english_spacing(context)
        num_predict = 1024                 # کاهش برای سرعت
        num_ctx = 8192
        temperature = 0.1
        models_to_try = ["gemma2:9b"]      # ✅ استفاده از gemma برای انگلیسی

    # پرامپت فارسی
    if language == "fa":
        system_prompt = f"""
شما یک پژوهشگر ارشد و نویسندهٔ حرفه‌ای گزارش‌های علمی-پژوهشی با ۲۰ سال سابقه هستید.

موضوع:
{topic}

بخش فعلی:
{section_name}

شما باید گزارشی بنویسید که:
- کاملاً مبتنی بر منابع معتبر باشد.
- ساختاری آکادمیک و حرفه‌ای داشته باشد.
- از جملات روان، دقیق و بدون ابهام استفاده کند.
- هیچ اطلاعاتی خارج از منابع اضافه نکند.
- در پایان هر پاراگراف، به منابع استناد کند (با ذکر شماره منبع).

قوانین نگارشی:
- هر پاراگراف حداقل ۳ جمله داشته باشد.
- از جملات کوتاه و واضح استفاده کن (حداکثر ۲۰ کلمه در هر جمله).
- از تکرار کلمات و عبارات خودداری کن.
- از فعل‌های «می‌باشد» و «می‌باشند» استفاده نکن.

قوانین اختصاصی بر اساس بخش:

**معرفی موضوع**:
- **فقط** تعریف و تاریخچه.
- **هرگز** به کاربردها، مزایا، چالش‌ها یا مثال‌ها اشاره نکن.
- این بخش **مقدمه** است، نه خلاصه‌ی کل گزارش.

**یافته‌های اصلی**:
- **فقط** نتایج پژوهشی و مشاهدات علمی.
- **تحت هیچ شرایطی** تعریف، کاربرد یا چالش نیاور.
- اگر مطلب جدیدی در منابع نیست، این بخش را کوتاه نگه دار.

**کاربردها و مزایا**:
- **فقط** کاربردهای عملی و مزایا.
- **هرگز** تعریف یا تاریخچه را تکرار نکن.
- مستقیم با مثال‌های عملی شروع کن.

**چالش‌ها و محدودیت‌ها**:
- **فقط** محدودیت‌های فنی، اخلاقی و عملی.
- **هرگز** تعریف یا کاربرد نیاور.

**جمع‌بندی**:
- **فقط** خلاصه‌ی کلی از یافته‌ها و چالش‌ها.
- **هرگز** مثال، شرکت، فناوری خاص یا کاربرد جزئی نیاور.
- کاملاً مختصر و مفید باشد (حداکثر ۱۰۰ کلمه).
"""
    else:
        system_prompt = f"""
You are an academic research writer.

Topic:
{topic}

Current section:
{section_name}

Write only this section of the research report.

Rules:
- Use only the provided sources.
- Do not add unsupported information.
- Write natural academic English.
- Do not translate from Persian.
- Avoid unnatural expressions.
- Avoid repetition.
- Each section must contain unique information.
- Never start every section with a definition of the topic.
- Do not repeat the introduction in other sections.
- Use clear academic style.
- Keep sentences readable.
- Do not write about the writing process.
- Do not include Markdown headings.
- Output only the final section content.
- Never write the section title.
- Never use Markdown headings like #, ##, or ###.
- Start directly with the first paragraph.
- Never output the section title.
- Never write headings.
- Do not start with "Main Findings", "Applications and Benefits", "Challenges and Limitations".
- Start directly with the paragraph content.

Section-specific rules:

If this is the Introduction section:
- Write ONLY: what the topic is, a short historical background, and the general concept.
- STRICTLY FORBIDDEN: applications, companies, industries, benefits, risks, challenges, examples of use cases.
- Maximum length: 2 paragraphs.

If this is Main Findings:
- Present only important research findings.
- Do not define the topic again.
- Do not repeat the introduction.

If this is Applications and Benefits:
- Explain practical uses and advantages only.
- Do not define artificial intelligence.
- Start directly with practical uses and benefits.

If this is Challenges and Limitations:
- Explain technical, ethical, and practical limitations only.

If this is the Conclusion section:
- Write a very short summary of the main points of the report (general findings and main challenges).
- Do NOT mention any specific examples, applications, companies, historical figures, or specific technologies (like NLP, robotics, neural networks, etc.).
- Do NOT list any techniques or methods.
- Do NOT repeat the definition of AI.
- Do NOT introduce new information.
- Keep it brief: maximum 100 words.
- Output only the summary paragraph.
"""

    if language == "fa":
        user_prompt = f"""
برای بخش «{section_name}» متن علمی تولید کن.

فقط اطلاعات مرتبط با همین بخش را از منابع زیر استفاده کن:

{context}
"""
    else:
        user_prompt = f"""
Write the "{section_name}" section.

Use only relevant information from these sources:

{context}
"""

    last_error = None
    for model_idx, current_model in enumerate(models_to_try):
        print(f"[Research] Trying model {model_idx+1}/{len(models_to_try)}: {current_model}")

        result = chat_with_ollama(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            num_predict=num_predict,
            num_ctx=num_ctx,
            model=current_model,
        )

        if not result:
            print(f"[Research] Model {current_model} returned no result.")
            continue

        section_text = result.strip()

        # برای انگلیسی اعتبارسنجی نمی‌کنیم (یا حداقل ساده‌تر)
        if language != "fa":
            return section_text

        is_valid, reason = validate_section(section_name, section_text, language)
        if is_valid:
            print(f"[Research] Valid section generated with {current_model}")
            if section_name == "conclusion":
                section_text = postprocess_conclusion(section_text)
            return section_text
        else:
            last_error = reason
            print(f"[Research] Model {current_model} failed validation: {reason}")
            continue

    print(f"[Research] All models failed for section: {section_name}. Last error: {last_error}")
    if language == "fa":
        return "اطلاعات کافی برای این بخش از منابع موجود استخراج نشد."
    else:
        return "Insufficient information was available for this section."


def strip_duplicate_section_title(text: str, language: str) -> str:
    if not text:
        return text
    text = re.sub(r"^#+\s*.*?\n+", "", text.strip(), count=1)
    if language == "fa":
        duplicate_titles = {
            "معرفی موضوع", "یافته‌های اصلی", "کاربردها و مزایا",
            "چالش‌ها و محدودیت‌ها", "جمع‌بندی"
        }
    else:
        duplicate_titles = {
            "introduction", "main findings", "findings",
            "applications and benefits", "challenges and limitations", "conclusion"
        }
    lines = text.splitlines()
    filtered_lines = [
        line for line in lines
        if line.strip().lower() not in {t.lower() for t in duplicate_titles}
    ]
    return "\n".join(filtered_lines).strip()


def is_valid_persian_report(text: str) -> bool:
    if not text or len(text.strip()) < 300:
        return False
    required_headings = {
        "## معرفی موضوع", "## یافته‌های اصلی",
        "## کاربردها و مزایا", "## چالش‌ها و محدودیت‌ها", "## جمع‌بندی"
    }
    return all(heading in text for heading in required_headings)


# ============================================================
# ساخت گزارش نهایی
# ============================================================

def build_research_overview(
    topic: str,
    language: str,
    processed_sources: list[dict[str, Any]],
) -> str:
    source_context: list[str] = []
    for index, source in enumerate(processed_sources, start=1):
        source_context.append(
            f"""
منبع {index}

عنوان:
{source.get("title", "")}

خلاصه:
{source.get("summary", "")}
""".strip()
        )
    context = "\n\n---\n\n".join(source_context)

    if language == "fa":
        section_structure = [
            ("introduction", "## معرفی موضوع"),
            ("findings", "## یافته‌های اصلی"),
            ("applications", "## کاربردها و مزایا"),
            ("challenges", "## چالش‌ها و محدودیت‌ها"),
            ("conclusion", "## جمع‌بندی"),
        ]
    else:
        section_structure = [
            ("introduction", "## Introduction"),
            ("findings", "## Main Findings"),
            ("applications", "## Applications and benefits"),
            ("challenges", "## Challenges and limitations"),
            ("conclusion", "## Conclusion"),
        ]

    section_context_builders = {
        "introduction": lambda ctx, t=topic: (
            f"""
Instructions:
Write only the introduction about: "{t}"
Include only:
- definition of {t}
- brief historical background
- general concept of the field
Do not mention:
- machine learning
- deep learning
- applications
- industries
- companies
- examples
- benefits
- risks
- challenges
Source:
{ctx[:250]}
"""
        ),
        "findings": lambda ctx, t=topic: (
            f"Focus only on research results and observations about: \"{t}\"\n"
            "Do not introduce the topic.\n"
            "Do not provide definitions.\n"
            "- important research findings\n"
            "- key discoveries\n"
            "- technical observations\n\n"
            "Sources:\n" + ctx
        ),
        "applications": lambda ctx, t=topic: (
            f"Focus only on practical applications and benefits of: \"{t}\"\n\n"
            "Sources:\n" + ctx
        ),
        "challenges": lambda ctx, t=topic: (
            f"Focus only on limitations, ethical issues, and technical challenges of: \"{t}\"\n\n"
            "Sources:\n" + ctx
        ),
        "conclusion": lambda ctx, t=topic: (
            f"Write only a very short summary of the report's main findings and overall challenges about: \"{t}\"\n"
            "Do not mention any specific examples, companies, historical figures, applications, or technologies.\n"
            "Do not repeat the definition of AI.\n"
            "Keep it brief (maximum 100 words).\n\n"
            "Sources:\n" + ctx[:2000]
        ),
    }

    sections: list[str] = []

    for section_name, heading in section_structure:
        print("[Research] Generating section:", section_name)

        section_context = section_context_builders[section_name](context)

        section_text = ""

        for attempt in range(SECTION_MAX_ATTEMPTS):
            section_text = generate_section(
                section_name=section_name,
                topic=topic,
                language=language,
                context=section_context,
            )

            if section_text is None:
                section_text = ""

            # برای انگلیسی اعتبارسنجی نمی‌کنیم
            if language == "en":
                break

            is_valid, invalid_reason = validate_section(section_name, section_text, language)

            if is_valid:
                break

            print(
                "[Research] Section invalid, retrying:",
                section_name,
                "attempt:",
                attempt + 1,
                "reason:",
                invalid_reason or "unknown",
            )

            if invalid_reason:
                section_context = (
                    section_context
                    + f"\n\n(Your previous attempt was rejected for this reason: "
                    f"\"{invalid_reason}\". Rewrite the section to fix this "
                    f"specific issue.)"
                )
            else:
                section_context = section_context + "\n\n(Please rewrite more concisely.)"

        else:
            print("[Research] Warning: section still invalid after retries:", section_name)

        if not section_text:
            if language == "fa":
                section_text = "اطلاعات کافی برای این بخش از منابع موجود استخراج نشد."
            else:
                section_text = "Insufficient information was available for this section."

        section_text = strip_duplicate_section_title(section_text, language)

        # برای فارسی ویرایش نگارشی (اختیاری)
        if language == "fa":
            section_text = polish_section(section_text, language)
        else:
            section_text = repair_english_text(section_text)

        sections.append(f"{heading}\n\n{section_text}")

    report = "\n\n---\n\n".join(sections)

    sources_section = format_sources(
        processed_sources=processed_sources,
        language=language,
    )

    full_report = f"{report}\n\n{sources_section}"

    if language == "fa" and not is_valid_persian_report(full_report):
        print("[Research] Warning: final Persian report failed quality check.")

    return full_report


# ============================================================
# نقطهٔ ورود اصلی
# ============================================================

def run_research(
    conversation_id: str,
    topic: str,
    language: str = "fa",
    max_sources: int = 3,
) -> dict[str, Any]:
    topic = (topic or "").strip()
    language = (language or "fa").strip().lower()

    try:
        max_sources = int(max_sources)
    except (TypeError, ValueError):
        max_sources = 3

    max_sources = max(1, min(max_sources, MAX_ALLOWED_SOURCES))

    if not topic:
        return {
            "answer": (
                "موضوع پژوهش مشخص نیست." if language == "fa"
                else "The research topic is missing."
            ),
            "sources": [],
            "sources_count": 0,
        }

    update_conversation(
        conversation_id=conversation_id,
        topic=topic,
        language=language,
    )

    clear_research_data(conversation_id)

    search_results = search_web(topic, max_results=max_sources * 5) or []

    print("[Research] Topic:", topic)
    print("[Research] Search results:", search_results)

    processed_sources = []
    seen_urls = set()
    seen_domains = set()

    for item in search_results:
        if len(processed_sources) >= max_sources:
            break

        url = ""
        search_title = "Untitled"

        try:
            if isinstance(item, str):
                url = item.strip()
            elif isinstance(item, dict):
                url = str(
                    item.get("url") or item.get("href") or item.get("link") or ""
                ).strip()
                search_title = str(item.get("title") or item.get("name") or "Untitled").strip()
            else:
                print("[Research] Unsupported search result:", repr(item))
                continue

            if any(
                bad in url.lower()
                for bad in [
                    "aclick", "adservice", "doubleclick", "googleadservices",
                    "utm_", "msclkid"
                ]
            ):
                print("[Research] Tracking URL skipped:", url)
                continue

            normalized_url = normalize_url(url)
            if not normalized_url:
                continue

            if normalized_url in seen_urls:
                print("[Research] Duplicate URL skipped:", url)
                continue
            seen_urls.add(normalized_url)

            domain_group = get_domain_group(url)
            if not domain_group:
                continue

            if domain_group in seen_domains:
                print("[Research] Duplicate domain skipped:", domain_group)
                continue

            print("[Research] Fetching:", url)

            html = fetch_page(url)
            if not html:
                continue

            title = extract_title(html)
            if not title or title == "بدون عنوان":
                title = search_title

            try:
                raw_text = extract_main_text(html, url=url)
            except TypeError:
                raw_text = extract_main_text(html)

            if not raw_text:
                continue

            cleaned_text = clean_extracted_text(raw_text)

            if len(cleaned_text) < MIN_SOURCE_TEXT_LENGTH:
                print("[Research] Text too short:", url)
                continue

            chunks = chunk_text(cleaned_text)
            if not chunks:
                continue

            print("[Research] Summarizing:", url)

            summary = summarize_with_ollama(
                text=cleaned_text,
                language=language,
                topic=topic,
            )

            if not summary:
                summary = cleaned_text[:1200]
                if language == "fa":
                    summary = normalize_persian_text(summary)

            source_id = save_source(
                conversation_id=conversation_id,
                title=title,
                url=url,
                raw_text=raw_text,
                clean_text=cleaned_text,
                summary=summary,
            )

            for chunk_index, chunk in enumerate(chunks):
                save_chunk(
                    conversation_id=conversation_id,
                    source_id=source_id,
                    chunk_index=chunk_index,
                    chunk_text=chunk,
                )

            processed_sources.append({
                "title": title,
                "url": url,
                "summary": summary,
                "chunks_count": len(chunks),
                "domain": domain_group,
            })

            seen_domains.add(domain_group)

            print("[Research] Source completed:", url, "domain:", domain_group)

        except Exception as error:
            print(
                "[Research] Processing error:",
                url,
                type(error).__name__,
                str(error),
            )
            continue

    if not processed_sources:
        return {
            "answer": (
                f'No processable source was found for "{topic}".'
                if language != "fa"
                else f"برای موضوع «{topic}» منبع قابل پردازشی پیدا نشد."
            ),
            "sources": [],
            "sources_count": 0,
            "topic": topic,
        }

    answer = build_research_overview(
        topic=topic,
        language=language,
        processed_sources=processed_sources,
    )

    return {
        "answer": answer,
        "sources": [source["url"] for source in processed_sources],
        "sources_count": len(processed_sources),
        "topic": topic,
    }