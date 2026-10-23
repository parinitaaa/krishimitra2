create table if not exists public.disease_observations (
    id bigserial primary key,
    farmer_id text not null,
    disease text not null,
    crop text,
    confidence double precision not null check (confidence >= 0 and confidence <= 1),
    severity text not null default 'Unknown',
    latitude double precision not null check (latitude between -90 and 90),
    longitude double precision not null check (longitude between -180 and 180),
    detected_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index if not exists idx_disease_observations_detected_at
    on public.disease_observations (detected_at desc);

create index if not exists idx_disease_observations_disease_time
    on public.disease_observations (disease, detected_at desc);

create index if not exists idx_disease_observations_location
    on public.disease_observations (latitude, longitude);
