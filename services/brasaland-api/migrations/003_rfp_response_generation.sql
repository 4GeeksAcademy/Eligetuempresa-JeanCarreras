BEGIN;

-- Extend rfp_tickets status to include response generation states
ALTER TABLE public.rfp_tickets DROP CONSTRAINT rfp_tickets_status_check;
ALTER TABLE public.rfp_tickets ADD CONSTRAINT rfp_tickets_status_check
    CHECK (status IN (
        'analizando',
        'descartado',
        'analisis_completo',
        'generando_borrador',
        'en_evaluacion',
        'needs_human_review'
    ));

-- Store generated draft proposal sections per department
CREATE TABLE public.rfp_response_drafts (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id uuid NOT NULL REFERENCES public.rfp_tickets(id) ON DELETE CASCADE,
    department text NOT NULL,
    iteration int NOT NULL DEFAULT 1,
    content text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (ticket_id, department, iteration)
);

-- Store structured evaluation results for each draft iteration
CREATE TABLE public.rfp_evaluation_results (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id uuid NOT NULL REFERENCES public.rfp_tickets(id) ON DELETE CASCADE,
    department text NOT NULL,
    iteration int NOT NULL DEFAULT 1,
    overall_pass bool NOT NULL,
    readability jsonb NOT NULL DEFAULT '{}'::jsonb,
    relevance jsonb NOT NULL DEFAULT '{}'::jsonb,
    compliance jsonb NOT NULL DEFAULT '{}'::jsonb,
    feedback_for_generator text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (ticket_id, department, iteration)
);

-- Handoff payload for Part 3
CREATE TABLE public.rfp_response_handoff (
    ticket_id uuid PRIMARY KEY REFERENCES public.rfp_tickets(id) ON DELETE CASCADE,
    handoff jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX rfp_response_drafts_ticket_idx ON public.rfp_response_drafts (ticket_id, department);
CREATE INDEX rfp_evaluation_results_ticket_idx ON public.rfp_evaluation_results (ticket_id, department);

ALTER TABLE public.rfp_response_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rfp_evaluation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rfp_response_handoff ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.rfp_response_drafts, public.rfp_evaluation_results, public.rfp_response_handoff
    FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.rfp_response_drafts,
    public.rfp_evaluation_results, public.rfp_response_handoff TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.rfp_response_drafts_id_seq,
    public.rfp_evaluation_results_id_seq TO service_role;

COMMIT;