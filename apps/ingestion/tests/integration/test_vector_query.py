from __future__ import annotations

import os
from uuid import uuid4

import psycopg
import pytest

pytestmark = pytest.mark.db_integration


def test_insert_and_query_nearest_vector() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for the database integration test")

    external_id = f"db-007-{uuid4()}"
    checksum = "a" * 64

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO documents (
                source, external_id, title, url, content, checksum
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                "fixture",
                external_id,
                "Synthetic DB-007 document",
                "https://example.invalid/db-007",
                "Synthetic content used only for the vector integration test.",
                checksum,
            ),
        )
        document_row = cursor.fetchone()
        assert document_row is not None
        document_id = document_row[0]

        cursor.executemany(
            """
            INSERT INTO chunks (document_id, chunk_index, content, embedding)
            VALUES (%s, %s, %s, %s::vector)
            """,
            [
                (document_id, 0, "nearest", "[1,0,0]"),
                (document_id, 1, "farther", "[0,1,0]"),
            ],
        )

        cursor.execute(
            """
            SELECT content, embedding <=> %s::vector AS cosine_distance
            FROM chunks
            WHERE document_id = %s
            ORDER BY cosine_distance
            LIMIT 1
            """,
            ("[1,0,0]", document_id),
        )
        nearest_row = cursor.fetchone()
        assert nearest_row is not None
        content, distance = nearest_row

        assert content == "nearest"
        assert float(distance) == pytest.approx(0.0)

        connection.rollback()
