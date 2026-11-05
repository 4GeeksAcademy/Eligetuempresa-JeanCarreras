BEGIN;

CREATE TABLE public.rfp_tickets (
    id uuid PRIMARY KEY,
    status text NOT NULL CHECK (status IN ('analizando', 'descartado', 'analisis_completo')),
    original_filename text NOT NULL,
    pdf_path text NOT NULL,
    handoff jsonb,
    classification_reason text,
    processing_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.rfp_documents (
    ticket_id uuid PRIMARY KEY REFERENCES public.rfp_tickets(id) ON DELETE CASCADE,
    markdown_path text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    readability_metrics jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(readability_metrics) = 'object'),
    classification jsonb NOT NULL CHECK (jsonb_typeof(classification) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.rfp_department_sections (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id uuid NOT NULL REFERENCES public.rfp_tickets(id) ON DELETE CASCADE,
    department text NOT NULL,
    contact text NOT NULL,
    key_aspects jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(key_aspects) = 'array'),
    source_excerpt text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (ticket_id, department)
);

CREATE INDEX rfp_tickets_created_at_idx ON public.rfp_tickets (created_at DESC);
CREATE INDEX rfp_tickets_status_idx ON public.rfp_tickets (status);

ALTER TABLE public.rfp_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rfp_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rfp_department_sections ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.rfp_tickets, public.rfp_documents, public.rfp_department_sections
    FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.rfp_tickets,
    public.rfp_documents, public.rfp_department_sections TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.rfp_department_sections_id_seq TO service_role;

COMMIT;