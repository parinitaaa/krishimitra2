-- migrations/000_baseline.sql
-- Baseline live schema reflected from Supabase (read-only verification snapshot)

-- 1. farmers table
CREATE TABLE IF NOT EXISTS public.farmers (
    phone text NOT NULL,
    name text DEFAULT 'Kisan bhai'::text,
    crops text[],
    location text,
    history jsonb DEFAULT '[]'::jsonb,
    messages jsonb DEFAULT '[]'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    soil_type text DEFAULT 'unknown'::text,
    last_seen timestamp with time zone DEFAULT now(),
    last_detection jsonb,
    lat double precision,
    lng double precision,
    language character varying,
    CONSTRAINT farmers_pkey PRIMARY KEY (phone)
);

-- 2. price_alerts table
CREATE TABLE IF NOT EXISTS public.price_alerts (
    id serial NOT NULL,
    phone text NOT NULL,
    commodity text NOT NULL,
    target_price numeric NOT NULL,
    direction text NOT NULL,
    active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    last_triggered_price numeric,
    CONSTRAINT price_alerts_pkey PRIMARY KEY (id)
);

-- 3. detections table
CREATE TABLE IF NOT EXISTS public.detections (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    phone text,
    disease_name text,
    crop_type text,
    severity integer,
    lat double precision,
    lng double precision,
    created_at timestamp with time zone DEFAULT now(),
    spread boolean DEFAULT false,
    processed boolean DEFAULT false,
    CONSTRAINT detections_pkey PRIMARY KEY (id)
);

-- 4. mandi_prices table
CREATE TABLE IF NOT EXISTS public.mandi_prices (
    id serial NOT NULL,
    state character varying NOT NULL,
    district character varying NOT NULL,
    market character varying NOT NULL,
    commodity character varying NOT NULL,
    variety character varying,
    min_price double precision,
    max_price double precision,
    modal_price double precision,
    arrival_date date NOT NULL,
    fetched_at timestamp without time zone,
    CONSTRAINT mandi_prices_pkey PRIMARY KEY (id),
    CONSTRAINT uq_market_commodity_date UNIQUE (market, commodity, variety, arrival_date)
);

CREATE INDEX IF NOT EXISTS ix_mandi_prices_commodity ON public.mandi_prices USING btree (commodity);
CREATE INDEX IF NOT EXISTS ix_mandi_prices_id ON public.mandi_prices USING btree (id);
CREATE INDEX IF NOT EXISTS ix_mandi_prices_market ON public.mandi_prices USING btree (market);
CREATE INDEX IF NOT EXISTS ix_mandi_prices_state ON public.mandi_prices USING btree (state);
