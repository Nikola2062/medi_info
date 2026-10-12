from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Sequence

from .models import CaptureSlot, IngredientRecord, ProductRecord, ScanSessionRecord, ScanUploadRecord, SourceRecord
from .normalization import normalize_search_text


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_document (
    id TEXT PRIMARY KEY,
    authority TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    jurisdiction_code TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    published_or_effective_at TEXT,
    content_hash TEXT NOT NULL,
    licence TEXT,
    raw_snapshot_location TEXT
);

CREATE TABLE IF NOT EXISTS registry_snapshot (
    id TEXT PRIMARY KEY,
    jurisdiction_code TEXT NOT NULL,
    source_document_id TEXT NOT NULL REFERENCES source_document(id),
    imported_at TEXT NOT NULL,
    published_at TEXT,
    record_count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('staging', 'published', 'superseded', 'quarantined'))
);

CREATE TABLE IF NOT EXISTS regulatory_product (
    id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES registry_snapshot(id) ON DELETE CASCADE,
    jurisdiction_code TEXT NOT NULL,
    registration_number TEXT NOT NULL,
    product_name_original TEXT NOT NULL,
    product_name_normalized TEXT NOT NULL,
    certificate_holder TEXT,
    certificate_holder_normalized TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    source_record_key TEXT,
    UNIQUE (snapshot_id, registration_number)
);

CREATE INDEX IF NOT EXISTS idx_product_registration ON regulatory_product(jurisdiction_code, registration_number);
CREATE INDEX IF NOT EXISTS idx_product_name ON regulatory_product(product_name_normalized);
CREATE INDEX IF NOT EXISTS idx_product_holder ON regulatory_product(certificate_holder_normalized);

CREATE TABLE IF NOT EXISTS product_ingredient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL REFERENCES regulatory_product(id) ON DELETE CASCADE,
    ingredient_name_original TEXT NOT NULL,
    ingredient_name_normalized TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ingredient_name ON product_ingredient(ingredient_name_normalized);

CREATE TABLE IF NOT EXISTS application_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scan_session (
    id TEXT PRIMARY KEY,
    jurisdiction_code TEXT NOT NULL,
    created_at TEXT NOT NULL,
    image_deletion_due_at TEXT NOT NULL,
    identity_state TEXT NOT NULL DEFAULT 'unable_to_identify',
    privacy_redaction_state TEXT NOT NULL DEFAULT 'not_assessed'
);

CREATE TABLE IF NOT EXISTS scan_upload (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES scan_session(id) ON DELETE CASCADE,
    slot TEXT NOT NULL CHECK (slot IN ('front', 'ingredients', 'identifier')),
    stored_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    byte_size INTEGER NOT NULL,
    quality_warnings_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    UNIQUE (session_id, slot),
    UNIQUE (session_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_scan_session_deletion_due
    ON scan_session(image_deletion_due_at);
"""


@dataclass(frozen=True)
class StoredProduct:
    id: str
    record: ProductRecord


@dataclass(frozen=True)
class PublishedRegistry:
    snapshot_id: str
    source: SourceRecord
    record_count: int
    published_at: datetime


class RegistryRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def publish_snapshot(self, source: SourceRecord, products: Sequence[ProductRecord]) -> PublishedRegistry:
        if source.jurisdiction_code != "HK":
            raise ValueError("The first importer only accepts the HK jurisdiction")
        if not products:
            raise ValueError("Refusing to publish an empty registry snapshot")

        registrations = [product.registration_number for product in products]
        if len(registrations) != len(set(registrations)):
            raise ValueError("Snapshot contains duplicate registration numbers")

        source_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source.url}:{source.content_hash}"))
        snapshot_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"HK:{source.content_hash}"))
        now = datetime.now(UTC)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """INSERT INTO source_document
                    (id, authority, title, url, jurisdiction_code, retrieved_at,
                     published_or_effective_at, content_hash, licence, raw_snapshot_location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        retrieved_at = excluded.retrieved_at,
                        raw_snapshot_location = excluded.raw_snapshot_location""",
                    (
                        source_id,
                        source.authority,
                        source.title,
                        source.url,
                        source.jurisdiction_code,
                        source.retrieved_at.isoformat(),
                        source.published_or_effective_at.isoformat() if source.published_or_effective_at else None,
                        source.content_hash,
                        source.licence,
                        source.raw_snapshot_location,
                    ),
                )
                connection.execute(
                    """INSERT OR IGNORE INTO registry_snapshot
                    (id, jurisdiction_code, source_document_id, imported_at, record_count, status)
                    VALUES (?, 'HK', ?, ?, ?, 'staging')""",
                    (snapshot_id, source_id, now.isoformat(), len(products)),
                )

                for product in products:
                    product_id = str(
                        uuid.uuid5(uuid.NAMESPACE_URL, f"{snapshot_id}:{product.registration_number}")
                    )
                    connection.execute(
                        """INSERT OR IGNORE INTO regulatory_product
                        (id, snapshot_id, jurisdiction_code, registration_number,
                         product_name_original, product_name_normalized, certificate_holder,
                         certificate_holder_normalized, status, source_record_key)
                        VALUES (?, ?, 'HK', ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            product_id,
                            snapshot_id,
                            product.registration_number,
                            product.product_name,
                            product.normalized_name,
                            product.certificate_holder,
                            product.normalized_holder,
                            product.status,
                            product.source_record_key,
                        ),
                    )
                    for ingredient in product.ingredients:
                        connection.execute(
                            """INSERT INTO product_ingredient
                            (product_id, ingredient_name_original, ingredient_name_normalized)
                            SELECT ?, ?, ? WHERE NOT EXISTS (
                                SELECT 1 FROM product_ingredient
                                WHERE product_id = ? AND ingredient_name_original = ?
                            )""",
                            (
                                product_id,
                                ingredient.name,
                                ingredient.normalized_name,
                                product_id,
                                ingredient.name,
                            ),
                        )

                previous = connection.execute(
                    "SELECT value FROM application_state WHERE key = 'current_snapshot:HK'"
                ).fetchone()
                if previous and previous["value"] != snapshot_id:
                    connection.execute(
                        "UPDATE registry_snapshot SET status = 'superseded' WHERE id = ?",
                        (previous["value"],),
                    )
                connection.execute(
                    "UPDATE registry_snapshot SET status = 'published', published_at = ? WHERE id = ?",
                    (now.isoformat(), snapshot_id),
                )
                connection.execute(
                    """INSERT INTO application_state(key, value) VALUES ('current_snapshot:HK', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                    (snapshot_id,),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        return PublishedRegistry(snapshot_id, source, len(products), now)

    def current_registry(self, jurisdiction: str = "HK") -> PublishedRegistry | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT rs.id, rs.record_count, rs.published_at, sd.*
                FROM application_state state
                JOIN registry_snapshot rs ON rs.id = state.value
                JOIN source_document sd ON sd.id = rs.source_document_id
                WHERE state.key = ? AND rs.status = 'published'""",
                (f"current_snapshot:{jurisdiction}",),
            ).fetchone()
            if not row:
                return None
            return PublishedRegistry(
                snapshot_id=row["id"],
                source=self._source_from_row(row),
                record_count=row["record_count"],
                published_at=datetime.fromisoformat(row["published_at"]),
            )

    def search(
        self,
        *,
        jurisdiction: str = "HK",
        registration_number: str | None = None,
        query: str | None = None,
        limit: int = 10,
    ) -> list[StoredProduct]:
        current = self.current_registry(jurisdiction)
        if not current:
            return []

        clauses = ["p.snapshot_id = ?"]
        parameters: list[object] = [current.snapshot_id]
        if registration_number:
            clauses.append("p.registration_number = ?")
            parameters.append(registration_number)
        elif query:
            normalized = normalize_search_text(query)
            clauses.append(
                """(p.product_name_normalized LIKE ? OR p.certificate_holder_normalized LIKE ?
                OR EXISTS (
                    SELECT 1 FROM product_ingredient search_i
                    WHERE search_i.product_id = p.id
                    AND search_i.ingredient_name_normalized LIKE ?
                ))"""
            )
            wildcard = f"%{normalized}%"
            parameters.extend((wildcard, wildcard, wildcard))
        else:
            return []
        parameters.append(limit)

        sql = f"""SELECT p.* FROM regulatory_product p
            WHERE {' AND '.join(clauses)}
            ORDER BY CASE WHEN p.product_name_normalized = ? THEN 0 ELSE 1 END,
                     p.product_name_original
            LIMIT ?"""
        # Exact-name ordering only matters for text search. Insert a harmless value otherwise.
        parameters.insert(-1, normalize_search_text(query or ""))

        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
            return [self._stored_product(connection, row) for row in rows]

    def get(self, product_id: str, jurisdiction: str = "HK") -> StoredProduct | None:
        current = self.current_registry(jurisdiction)
        if not current:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM regulatory_product WHERE id = ? AND snapshot_id = ?",
                (product_id, current.snapshot_id),
            ).fetchone()
            return self._stored_product(connection, row) if row else None

    def create_scan_session(
        self,
        *,
        jurisdiction: str,
        created_at: datetime,
        image_deletion_due_at: datetime,
    ) -> ScanSessionRecord:
        session_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO scan_session
                (id, jurisdiction_code, created_at, image_deletion_due_at)
                VALUES (?, ?, ?, ?)""",
                (
                    session_id,
                    jurisdiction,
                    created_at.isoformat(),
                    image_deletion_due_at.isoformat(),
                ),
            )
            connection.commit()
        return ScanSessionRecord(
            id=session_id,
            jurisdiction_code=jurisdiction,
            created_at=created_at,
            image_deletion_due_at=image_deletion_due_at,
        )

    def get_scan_session(self, session_id: str) -> ScanSessionRecord | None:
        with self._connect() as connection:
            session_row = connection.execute(
                "SELECT * FROM scan_session WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not session_row:
                return None
            upload_rows = connection.execute(
                "SELECT * FROM scan_upload WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            ).fetchall()
            return self._scan_session_from_rows(session_row, upload_rows)

    def find_scan_upload_by_idempotency(
        self,
        session_id: str,
        idempotency_key: str,
    ) -> ScanUploadRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM scan_upload
                WHERE session_id = ? AND idempotency_key = ?""",
                (session_id, idempotency_key),
            ).fetchone()
            return self._scan_upload_from_row(row) if row else None

    def save_scan_upload(self, upload: ScanUploadRecord) -> str | None:
        """Save or replace a capture slot and return the replaced file path."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT stored_path FROM scan_upload WHERE session_id = ? AND slot = ?",
                    (upload.session_id, upload.slot.value),
                ).fetchone()
                if existing:
                    connection.execute(
                        "DELETE FROM scan_upload WHERE session_id = ? AND slot = ?",
                        (upload.session_id, upload.slot.value),
                    )
                connection.execute(
                    """INSERT INTO scan_upload
                    (id, session_id, slot, stored_path, mime_type, width, height,
                     byte_size, quality_warnings_json, created_at, idempotency_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        upload.id,
                        upload.session_id,
                        upload.slot.value,
                        upload.stored_path,
                        upload.mime_type,
                        upload.width,
                        upload.height,
                        upload.byte_size,
                        json.dumps(upload.quality_warnings),
                        upload.created_at.isoformat(),
                        upload.idempotency_key,
                    ),
                )
                connection.commit()
                return existing["stored_path"] if existing else None
            except Exception:
                connection.rollback()
                raise

    def delete_scan_session(self, session_id: str) -> list[str] | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                exists = connection.execute(
                    "SELECT 1 FROM scan_session WHERE id = ?",
                    (session_id,),
                ).fetchone()
                if not exists:
                    connection.rollback()
                    return None
                paths = [
                    row["stored_path"]
                    for row in connection.execute(
                        "SELECT stored_path FROM scan_upload WHERE session_id = ?",
                        (session_id,),
                    ).fetchall()
                ]
                connection.execute("DELETE FROM scan_session WHERE id = ?", (session_id,))
                connection.commit()
                return paths
            except Exception:
                connection.rollback()
                raise

    def expired_scan_session_ids(self, now: datetime) -> list[str]:
        with self._connect() as connection:
            return [
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM scan_session WHERE image_deletion_due_at <= ?",
                    (now.isoformat(),),
                ).fetchall()
            ]

    @staticmethod
    def _scan_upload_from_row(row: sqlite3.Row) -> ScanUploadRecord:
        return ScanUploadRecord(
            id=row["id"],
            session_id=row["session_id"],
            slot=CaptureSlot(row["slot"]),
            stored_path=row["stored_path"],
            mime_type=row["mime_type"],
            width=row["width"],
            height=row["height"],
            byte_size=row["byte_size"],
            quality_warnings=tuple(json.loads(row["quality_warnings_json"])),
            created_at=datetime.fromisoformat(row["created_at"]),
            idempotency_key=row["idempotency_key"],
        )

    @classmethod
    def _scan_session_from_rows(
        cls,
        session_row: sqlite3.Row,
        upload_rows: Sequence[sqlite3.Row],
    ) -> ScanSessionRecord:
        return ScanSessionRecord(
            id=session_row["id"],
            jurisdiction_code=session_row["jurisdiction_code"],
            created_at=datetime.fromisoformat(session_row["created_at"]),
            image_deletion_due_at=datetime.fromisoformat(session_row["image_deletion_due_at"]),
            uploads=tuple(cls._scan_upload_from_row(row) for row in upload_rows),
        )

    @staticmethod
    def _stored_product(connection: sqlite3.Connection, row: sqlite3.Row) -> StoredProduct:
        ingredient_rows = connection.execute(
            """SELECT ingredient_name_original, ingredient_name_normalized
            FROM product_ingredient WHERE product_id = ? ORDER BY id""",
            (row["id"],),
        ).fetchall()
        ingredients = tuple(
            IngredientRecord(item["ingredient_name_original"], item["ingredient_name_normalized"])
            for item in ingredient_rows
        )
        return StoredProduct(
            id=row["id"],
            record=ProductRecord(
                registration_number=row["registration_number"],
                product_name=row["product_name_original"],
                normalized_name=row["product_name_normalized"],
                certificate_holder=row["certificate_holder"],
                normalized_holder=row["certificate_holder_normalized"],
                status=row["status"],
                source_record_key=row["source_record_key"],
                ingredients=ingredients,
            ),
        )

    @staticmethod
    def _source_from_row(row: sqlite3.Row) -> SourceRecord:
        return SourceRecord(
            authority=row["authority"],
            title=row["title"],
            url=row["url"],
            jurisdiction_code=row["jurisdiction_code"],
            retrieved_at=datetime.fromisoformat(row["retrieved_at"]),
            published_or_effective_at=(
                datetime.fromisoformat(row["published_or_effective_at"])
                if row["published_or_effective_at"]
                else None
            ),
            content_hash=row["content_hash"],
            licence=row["licence"],
            raw_snapshot_location=row["raw_snapshot_location"],
        )
