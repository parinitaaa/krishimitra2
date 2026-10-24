-- Migration 002: Outbreak support for disease_cases
-- Idempotent: safe to run multiple times

-- Add outbreak_evaluated_at to disease_cases
ALTER TABLE disease_cases
    ADD COLUMN IF NOT EXISTS outbreak_evaluated_at TIMESTAMPTZ;

-- Add proactive_opt_in to farmers (default true)
ALTER TABLE farmers
    ADD COLUMN IF NOT EXISTS proactive_opt_in BOOLEAN DEFAULT TRUE;

-- Create outbreak_alerts_sent table for deduplication
CREATE TABLE IF NOT EXISTS outbreak_alerts_sent (
    id          BIGSERIAL PRIMARY KEY,
    case_id     UUID NOT NULL,
    recipient_phone TEXT NOT NULL,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (case_id, recipient_phone)
);

CREATE INDEX IF NOT EXISTS idx_outbreak_alerts_sent_recipient
    ON outbreak_alerts_sent (recipient_phone, sent_at);
