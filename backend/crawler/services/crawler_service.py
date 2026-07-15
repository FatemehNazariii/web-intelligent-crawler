from __future__ import annotations

import socket
import time
from typing import Final
from urllib.parse import urlsplit

import certifi
import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_TIMEOUT: Final[tuple[int, int]] = (10, 30)

DEFAULT_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "WebIntelligentCrawler/1.0 "
        "(academic research project; contact: local-development)"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": (
        "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

ALLOWED_CONTENT_TYPES: Final[tuple[str, ...]] = (
    "text/html",
    "application/xhtml+xml",
)

MAX_RESPONSE_BYTES: Final[int] = 15 * 1024 * 1024
MIN_HTML_LENGTH: Final[int] = 200


def create_http_session() -> requests.Session:
    """
    ساخت Session مشترک با retry محدود برای خطاهای موقت شبکه.
    """

    retry_strategy = Retry(
        total=3,
        connect=3,
        read=2,
        status=2,
        backoff_factor=0.8,
        status_forcelist=(
            408,
            429,
            500,
            502,
            503,
            504,
        ),
        allowed_methods=frozenset(
            {
                "GET",
                "HEAD",
            }
        ),
        raise_on_status=False,
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=20,
        pool_maxsize=20,
    )

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    session.mount(
        "http://",
        adapter,
    )

    session.mount(
        "https://",
        adapter,
    )

    return session


HTTP_SESSION = create_http_session()


def validate_url(url: str) -> str | None:
    """
    اعتبارسنجی اولیه URL.

    فقط پروتکل‌های HTTP و HTTPS پذیرفته می‌شوند.
    """

    if not isinstance(url, str):
        return None

    cleaned_url = url.strip()

    if not cleaned_url:
        return None

    try:
        parts = urlsplit(cleaned_url)
    except ValueError:
        return None

    if parts.scheme.lower() not in {
        "http",
        "https",
    }:
        return None

    if not parts.hostname:
        return None

    return cleaned_url


def resolve_hostname(url: str) -> bool:
    """
    بررسی اولیه DNS دامنه.

    این تابع مانع اجرای درخواست نمی‌شود، اما خطای DNS را
    زودتر و با پیام واضح‌تری ثبت می‌کند.
    """

    try:
        hostname = urlsplit(url).hostname

        if not hostname:
            return False

        socket.getaddrinfo(
            hostname,
            443,
            type=socket.SOCK_STREAM,
        )

        return True

    except socket.gaierror as error:
        print(
            f"[Crawler][DNS] "
            f"hostname={hostname!r}, "
            f"error={error}"
        )

        return False

    except Exception as error:
        print(
            f"[Crawler][DNS-Unexpected] "
            f"{type(error).__name__}: {error}"
        )

        return False


def is_supported_content_type(
    response: Response,
) -> bool:
    """
    بررسی نوع محتوای پاسخ.
    """

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
        .split(";")[0]
        .strip()
        .lower()
    )

    return any(
        allowed_type in content_type
        for allowed_type in ALLOWED_CONTENT_TYPES
    )


def detect_encoding(
    response: Response,
) -> str:
    """
    انتخاب encoding مناسب برای HTML.
    """

    declared_encoding = (
        response.encoding or ""
    ).strip()

    if (
        declared_encoding
        and declared_encoding.lower()
        not in {
            "iso-8859-1",
            "ascii",
        }
    ):
        return declared_encoding

    apparent_encoding = (
        response.apparent_encoding or ""
    ).strip()

    if apparent_encoding:
        return apparent_encoding

    return "utf-8"


def fetch_page(
    url: str,
    timeout: int | tuple[int, int] = DEFAULT_TIMEOUT,
    *,
    check_dns: bool = False,
) -> str | None:
    """
    دریافت HTML صفحه وب با مدیریت خطا، retry و محدودیت حجم.

    پارامترها:
    - url: آدرس صفحه
    - timeout: یک عدد یا زوج connect/read timeout
    - check_dns: بررسی صریح DNS پیش از درخواست

    خروجی:
    - متن HTML در صورت موفقیت
    - None در صورت خطا
    """

    validated_url = validate_url(
        url
    )

    if not validated_url:
        print(
            f"[Crawler] Invalid URL: {url!r}"
        )

        return None

    if check_dns and not resolve_hostname(
        validated_url
    ):
        return None

    started_at = time.perf_counter()

    try:
        response = HTTP_SESSION.get(
            validated_url,
            timeout=timeout,
            allow_redirects=True,
            verify=certifi.where(),
            stream=True,
        )

        elapsed = (
            time.perf_counter()
            - started_at
        )

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        content_length_header = (
            response.headers.get(
                "Content-Length"
            )
        )

        print(
            f"[Crawler] status={response.status_code} "
            f"url={response.url} "
            f"elapsed={elapsed:.2f}s"
        )

        print(
            f"[Crawler] content-type={content_type or 'unknown'} "
            f"content-length={content_length_header or 'unknown'}"
        )

        if response.status_code == 403:
            print(
                "[Crawler][HTTP] Access denied with status 403. "
                "The website may block automated requests."
            )

        response.raise_for_status()

        if not is_supported_content_type(
            response
        ):
            print(
                "[Crawler] Unsupported content type: "
                f"{content_type or 'unknown'}"
            )

            response.close()
            return None

        if content_length_header:
            try:
                declared_size = int(
                    content_length_header
                )

                if declared_size > MAX_RESPONSE_BYTES:
                    print(
                        "[Crawler] Response is too large: "
                        f"{declared_size} bytes"
                    )

                    response.close()
                    return None

            except ValueError:
                pass

        content_chunks: list[bytes] = []
        total_bytes = 0

        for chunk in response.iter_content(
            chunk_size=64 * 1024,
        ):
            if not chunk:
                continue

            total_bytes += len(chunk)

            if total_bytes > MAX_RESPONSE_BYTES:
                print(
                    "[Crawler] Response exceeded maximum size: "
                    f"{MAX_RESPONSE_BYTES} bytes"
                )

                response.close()
                return None

            content_chunks.append(
                chunk
            )

        response.close()

        raw_content = b"".join(
            content_chunks
        )

        print(
            f"[Crawler] downloaded-bytes={len(raw_content)}"
        )

        if not raw_content:
            print(
                "[Crawler] Empty response body"
            )

            return None

        response._content = raw_content
        response.encoding = detect_encoding(
            response
        )

        html = response.text.strip()

        if len(html) < MIN_HTML_LENGTH:
            print(
                "[Crawler] HTML too short: "
                f"{len(html)} characters"
            )

            return None

        return html

    except requests.exceptions.SSLError as error:
        print(
            f"[Crawler][SSL] "
            f"url={validated_url}, "
            f"error={error}"
        )

    except requests.exceptions.ConnectTimeout:
        print(
            f"[Crawler][ConnectTimeout] "
            f"url={validated_url}"
        )

    except requests.exceptions.ReadTimeout:
        print(
            f"[Crawler][ReadTimeout] "
            f"url={validated_url}"
        )

    except requests.exceptions.Timeout as error:
        print(
            f"[Crawler][Timeout] "
            f"url={validated_url}, "
            f"error={error}"
        )

    except requests.exceptions.TooManyRedirects as error:
        print(
            f"[Crawler][Redirect] "
            f"url={validated_url}, "
            f"error={error}"
        )

    except requests.exceptions.HTTPError as error:
        status = (
            error.response.status_code
            if error.response is not None
            else "unknown"
        )

        final_url = (
            error.response.url
            if error.response is not None
            else validated_url
        )

        print(
            f"[Crawler][HTTP] "
            f"status={status}, "
            f"url={final_url}, "
            f"error={error}"
        )

    except requests.exceptions.ConnectionError as error:
        error_text = str(
            error
        )

        if (
            "NameResolutionError" in error_text
            or "getaddrinfo failed" in error_text
        ):
            print(
                f"[Crawler][DNS] "
                f"url={validated_url}, "
                f"error={error}"
            )
        else:
            print(
                f"[Crawler][Connection] "
                f"url={validated_url}, "
                f"error={error}"
            )

    except requests.exceptions.RequestException as error:
        print(
            f"[Crawler][Request] "
            f"url={validated_url}, "
            f"error={error}"
        )

    except UnicodeError as error:
        print(
            f"[Crawler][Encoding] "
            f"url={validated_url}, "
            f"error={error}"
        )

    except Exception as error:
        print(
            f"[Crawler][Unexpected] "
            f"url={validated_url}, "
            f"type={type(error).__name__}, "
            f"error={error}"
        )

    return None