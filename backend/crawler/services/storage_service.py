import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db.sqlite3"


def get_connection() -> sqlite3.Connection:
    """
    ایجاد اتصال به دیتابیس SQLite پروژه.
    """

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_storage() -> None:
    """
    ساخت جدول‌های موردنیاز دستیار پژوهشی.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS research_conversations (
            id TEXT PRIMARY KEY,
            current_topic TEXT,
            language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS research_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id)
                REFERENCES research_conversations(id)
                ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS research_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            title TEXT,
            url TEXT NOT NULL,
            raw_text TEXT,
            clean_text TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id)
                REFERENCES research_conversations(id)
                ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS research_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id)
                REFERENCES research_conversations(id)
                ON DELETE CASCADE,
            FOREIGN KEY (source_id)
                REFERENCES research_sources(id)
                ON DELETE CASCADE
        )
        """
    )

    connection.commit()
    connection.close()


def create_conversation(
    conversation_id: str,
    topic: str | None = None,
    language: str | None = None
) -> None:
    initialize_storage()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO research_conversations (
            id,
            current_topic,
            language
        )
        VALUES (?, ?, ?)
        """,
        (
            conversation_id,
            topic,
            language
        )
    )

    connection.commit()
    connection.close()


def update_conversation(
    conversation_id: str,
    topic: str | None = None,
    language: str | None = None
) -> None:
    create_conversation(
        conversation_id=conversation_id,
        topic=topic,
        language=language
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE research_conversations
        SET
            current_topic = COALESCE(?, current_topic),
            language = COALESCE(?, language),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            topic,
            language,
            conversation_id
        )
    )

    connection.commit()
    connection.close()


def save_message(
    conversation_id: str,
    role: str,
    content: str
) -> None:
    create_conversation(conversation_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO research_messages (
            conversation_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            conversation_id,
            role,
            content
        )
    )

    connection.commit()
    connection.close()


def get_messages(
    conversation_id: str,
    limit: int = 20
) -> list[dict[str, Any]]:
    initialize_storage()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT role, content, created_at
        FROM research_messages
        WHERE conversation_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            conversation_id,
            limit
        )
    )

    rows = cursor.fetchall()
    connection.close()

    return [
        dict(row)
        for row in reversed(rows)
    ]


def clear_research_data(conversation_id: str) -> None:
    """
    حذف منابع و chunkهای تحقیق قبلی یک گفتگو.
    پیام‌های گفتگو حذف نمی‌شوند.
    """

    initialize_storage()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM research_chunks
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    cursor.execute(
        """
        DELETE FROM research_sources
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    connection.commit()
    connection.close()


def save_source(
    conversation_id: str,
    title: str,
    url: str,
    raw_text: str,
    clean_text: str,
    summary: str
) -> int:
    initialize_storage()
    create_conversation(conversation_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO research_sources (
            conversation_id,
            title,
            url,
            raw_text,
            clean_text,
            summary
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            conversation_id,
            title,
            url,
            raw_text,
            clean_text,
            summary
        )
    )

    source_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return int(source_id)


def save_chunk(
    conversation_id: str,
    source_id: int,
    chunk_index: int,
    chunk_text: str
) -> None:
    initialize_storage()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO research_chunks (
            conversation_id,
            source_id,
            chunk_index,
            chunk_text
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            conversation_id,
            source_id,
            chunk_index,
            chunk_text
        )
    )

    connection.commit()
    connection.close()


def get_sources(
    conversation_id: str
) -> list[dict[str, Any]]:
    initialize_storage()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            title,
            url,
            summary,
            created_at
        FROM research_sources
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,)
    )

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


def get_chunks(
    conversation_id: str
) -> list[dict[str, Any]]:
    initialize_storage()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            research_chunks.id,
            research_chunks.source_id,
            research_chunks.chunk_index,
            research_chunks.chunk_text,
            research_sources.title,
            research_sources.url
        FROM research_chunks
        JOIN research_sources
            ON research_sources.id = research_chunks.source_id
        WHERE research_chunks.conversation_id = ?
        ORDER BY research_chunks.id ASC
        """,
        (conversation_id,)
    )

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


def has_sources(conversation_id: str) -> bool:
    initialize_storage()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT EXISTS(
            SELECT 1
            FROM research_sources
            WHERE conversation_id = ?
            LIMIT 1
        ) AS source_exists
        """,
        (conversation_id,)
    )

    row = cursor.fetchone()
    connection.close()

    return bool(row["source_exists"]) if row else False