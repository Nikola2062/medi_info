BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE jurisdiction (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE CHECK (code ~ '^[A-Z]{2}$'),
    name text NOT NULL,
    default_locale text NOT NULL
);

INSERT INTO jurisdiction (code, name, default_locale)
VALUES ('HK', 'Hong Kong', 'zh-Hant-HK')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE source_document (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    authority text NOT NULL,
    title text NOT NULL,
    url text NOT NULL,
    jurisdiction_id uuid NOT NULL REFERENCES jurisdiction(id),
    retrieved_at timestamptz NOT NULL,
    published_or_effective_at timestamptz,
    content_hash text NOT NULL CHECK (content_hash ~ '^[a-f0-9]{64}$'),
    licence text,
    raw_snapshot_location text NOT NULL,
    UNIQUE (url, content_hash)
);

CREATE TABLE registry_snapshot (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    jurisdiction_id uuid NOT NULL REFERENCES jurisdiction(id),
    source_document_id uuid NOT NULL REFERENCES source_document(id),
    imported_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    record_count integer NOT NULL CHECK (record_count > 0),
    status text NOT NULL CHECK (status IN ('staging', 'published', 'superseded', 'quarantined'))
);

CREATE UNIQUE INDEX one_published_registry_per_jurisdiction
    ON registry_snapshot (jurisdiction_id)
    WHERE status = 'published';

CREATE TABLE regulatory_product (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_id uuid NOT NULL REFERENCES registry_snapshot(id) ON DELETE CASCADE,
    jurisdiction_id uuid NOT NULL REFERENCES jurisdiction(id),
    registration_number text NOT NULL,
    product_name_original text NOT NULL,
    product_name_normalized text NOT NULL,
    legal_classification text,
    sale_requirement text,
    certificate_holder text,
    certificate_holder_normalized text NOT NULL DEFAULT '',
    manufacturer text,
    registration_date date,
    status text NOT NULL,
    source_record_key text,
    valid_from timestamptz,
    valid_to timestamptz,
    UNIQUE (snapshot_id, registration_number)
);

CREATE INDEX regulatory_product_registration_idx
    ON regulatory_product (jurisdiction_id, registration_number);
CREATE INDEX regulatory_product_name_trgm_idx
    ON regulatory_product USING gin (product_name_normalized gin_trgm_ops);
CREATE INDEX regulatory_product_holder_trgm_idx
    ON regulatory_product USING gin (certificate_holder_normalized gin_trgm_ops);

CREATE TABLE product_ingredient (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id uuid NOT NULL REFERENCES regulatory_product(id) ON DELETE CASCADE,
    ingredient_name_original text NOT NULL,
    ingredient_name_normalized text NOT NULL,
    strength_value numeric,
    strength_unit text,
    salt_or_form text
);

CREATE INDEX product_ingredient_name_trgm_idx
    ON product_ingredient USING gin (ingredient_name_normalized gin_trgm_ops);

COMMIT;
