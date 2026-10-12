BEGIN;

CREATE TABLE scan_session (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    jurisdiction_id uuid NOT NULL REFERENCES jurisdiction(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    image_deletion_due_at timestamptz NOT NULL,
    extracted_fields_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    matched_product_id uuid REFERENCES regulatory_product(id),
    identity_state text NOT NULL DEFAULT 'unable_to_identify' CHECK (
        identity_state IN (
            'confirmed',
            'likely_user_confirmation_required',
            'candidate_only',
            'unable_to_identify',
            'conflicting_evidence',
            'unsupported_product_type'
        )
    ),
    user_confirmed_at timestamptz,
    privacy_redaction_state text NOT NULL DEFAULT 'not_assessed' CHECK (
        privacy_redaction_state IN ('not_assessed', 'warning_required', 'redacted', 'clear')
    ),
    CHECK (image_deletion_due_at > created_at)
);

CREATE INDEX scan_session_deletion_due_idx ON scan_session(image_deletion_due_at);

CREATE TABLE scan_upload (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES scan_session(id) ON DELETE CASCADE,
    slot text NOT NULL CHECK (slot IN ('front', 'ingredients', 'identifier')),
    stored_object_key text NOT NULL,
    mime_type text NOT NULL CHECK (mime_type IN ('image/jpeg')),
    width integer NOT NULL CHECK (width > 0),
    height integer NOT NULL CHECK (height > 0),
    byte_size integer NOT NULL CHECK (byte_size > 0),
    quality_warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    idempotency_key text NOT NULL,
    UNIQUE (session_id, slot),
    UNIQUE (session_id, idempotency_key)
);

COMMIT;
