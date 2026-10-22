BEGIN;

CREATE TABLE public.telemetry_events (
    event_id uuid PRIMARY KEY,
    timestamp timestamptz NOT NULL,
    event_type text NOT NULL,
    service text NOT NULL,
    session_id text,
    user_id text,
    schema_version text NOT NULL CHECK (schema_version = '1.0.0'),
    request_id text NOT NULL CHECK (length(request_id) > 0),
    tags jsonb NOT NULL CHECK (jsonb_typeof(tags) = 'object'),
    received_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX telemetry_events_timestamp_idx ON public.telemetry_events (timestamp);
CREATE INDEX telemetry_events_event_type_idx ON public.telemetry_events (event_type);
CREATE INDEX telemetry_events_tags_idx ON public.telemetry_events USING gin (tags);

ALTER TABLE public.telemetry_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.telemetry_events FROM PUBLIC, anon, authenticated, service_role;
GRANT INSERT, SELECT ON public.telemetry_events TO service_role;

COMMIT;