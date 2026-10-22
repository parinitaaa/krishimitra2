-- migrations/001_consolidated_state.sql
-- Migration 001: Consolidate database layer, conversation state, cases, and schema enhancements

-- 1. Farmers table enhancements
ALTER TABLE IF EXISTS public.farmers ALTER COLUMN name DROP DEFAULT;
UPDATE public.farmers SET name = NULL WHERE name = 'Kisan bhai';

ALTER TABLE IF EXISTS public.farmers ADD COLUMN IF NOT EXISTS onboarding_step text DEFAULT 'new';
ALTER TABLE IF EXISTS public.farmers ADD COLUMN IF NOT EXISTS water_source text;
ALTER TABLE IF EXISTS public.farmers ADD COLUMN IF NOT EXISTS state text;
ALTER TABLE IF EXISTS public.farmers ADD COLUMN IF NOT EXISTS district text;
ALTER TABLE IF EXISTS public.farmers ADD COLUMN IF NOT EXISTS farm_size_acres numeric;
ALTER TABLE IF EXISTS public.farmers ADD COLUMN IF NOT EXISTS last_message_at timestamp with time zone;

-- Backfill onboarding_step:
-- 'done' if language, name, and (lat/lng or location) are all present;
-- otherwise the first missing step.
UPDATE public.farmers
SET onboarding_step = CASE
    WHEN language IS NOT NULL AND TRIM(language) <> ''
         AND name IS NOT NULL AND TRIM(name) <> ''
         AND ((lat IS NOT NULL AND lng IS NOT NULL) OR (location IS NOT NULL AND TRIM(location) <> '')) THEN 'done'
    WHEN language IS NULL OR TRIM(language) = '' THEN 'ask_language'
    WHEN name IS NULL OR TRIM(name) = '' THEN 'ask_name'
    ELSE 'ask_location'
END
WHERE onboarding_step IS NULL OR onboarding_step = 'new';

-- 2. Price alerts enhancements
ALTER TABLE IF EXISTS public.price_alerts ADD COLUMN IF NOT EXISTS market text;
ALTER TABLE IF EXISTS public.price_alerts ADD COLUMN IF NOT EXISTS last_triggered_at timestamp with time zone;

-- 3. New table: conversation_state
CREATE TABLE IF NOT EXISTS public.conversation_state (
    phone text PRIMARY KEY,
    flow text,
    step text,
    data jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- 4. New table: chat_history
CREATE TABLE IF NOT EXISTS public.chat_history (
    id bigserial PRIMARY KEY,
    phone text NOT NULL,
    role text NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_history_phone_created ON public.chat_history (phone, created_at);

-- 5. New table: processed_messages (for Twilio idempotency / deduplication)
CREATE TABLE IF NOT EXISTS public.processed_messages (
    message_sid text PRIMARY KEY,
    created_at timestamp with time zone DEFAULT now()
);

-- 6. New table: disease_cases
CREATE TABLE IF NOT EXISTS public.disease_cases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone text NOT NULL,
    crop text,
    disease text,
    status text DEFAULT 'open',
    confidence double precision,
    severity_level text,
    severity_score integer,
    severity_source text DEFAULT 'unknown',
    lat double precision,
    lng double precision,
    spread_modes text[],
    image_url text,
    created_at timestamp with time zone DEFAULT now(),
    last_followup_at timestamp with time zone,
    next_followup_at timestamp with time zone,
    followup_count integer DEFAULT 0,
    resolved_at timestamp with time zone
);
CREATE INDEX IF NOT EXISTS ix_disease_cases_phone ON public.disease_cases (phone);
CREATE INDEX IF NOT EXISTS ix_disease_cases_lat_lng ON public.disease_cases (lat, lng);
CREATE INDEX IF NOT EXISTS ix_disease_cases_next_followup ON public.disease_cases (next_followup_at);

-- 7. New table: case_updates
CREATE TABLE IF NOT EXISTS public.case_updates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id uuid REFERENCES public.disease_cases(id) ON DELETE CASCADE,
    image_url text,
    farmer_reported_change text,
    note text,
    created_at timestamp with time zone DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_case_updates_case_id ON public.case_updates (case_id);

-- 8. New table: outbreak_alerts_sent
CREATE TABLE IF NOT EXISTS public.outbreak_alerts_sent (
    id bigserial PRIMARY KEY,
    case_id uuid REFERENCES public.disease_cases(id) ON DELETE CASCADE,
    recipient_phone text NOT NULL,
    sent_at timestamp with time zone DEFAULT now(),
    CONSTRAINT uq_outbreak_case_recipient UNIQUE (case_id, recipient_phone)
);
CREATE INDEX IF NOT EXISTS ix_outbreak_alerts_sent_case ON public.outbreak_alerts_sent (case_id);
CREATE INDEX IF NOT EXISTS ix_outbreak_alerts_sent_phone ON public.outbreak_alerts_sent (recipient_phone);
