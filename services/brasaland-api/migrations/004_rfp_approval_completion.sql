BEGIN;

-- Extend rfp_tickets status to include approval completion states
ALTER TABLE public.rfp_tickets DROP CONSTRAINT rfp_tickets_status_check;
ALTER TABLE public.rfp_tickets ADD CONSTRAINT rfp_tickets_status_check
    CHECK (status IN (
        -- Part 1: Intake & Analysis
        'analizando',
        'descartado',
        'analisis_completo',
        -- Part 2: Response Generation
        'generando_borrador',
        'en_evaluacion',
        'needs_human_review',
        -- Part 3: Approval & Closure
        'esperando_aprobacion',
        'terminado'
    ));

-- Department-level approval status for Part 3
CREATE TABLE public.rfp_approval_status (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id uuid NOT NULL REFERENCES public.rfp_tickets(id) ON DELETE CASCADE,
    department text NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'changes_requested', 'in_arbitration')),
    approver text NOT NULL DEFAULT '',
    decision text
        CHECK (decision IS NULL OR decision IN ('approved', 'rejected', 'changes_requested')),
    comment text NOT NULL DEFAULT '',
    approved_at timestamptz,
    rejected_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (ticket_id, department)
);

-- Final consolidated RFP document
CREATE TABLE public.rfp_final_document (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id uuid NOT NULL REFERENCES public.rfp_tickets(id) ON DELETE CASCADE,
    content jsonb NOT NULL DEFAULT '{}'::jsonb,
    rendered text NOT NULL DEFAULT '',
    version text NOT NULL DEFAULT '1.0',
    generated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (ticket_id)
);

-- Audit trail / tracing log for Part 3 node execution
CREATE TABLE public.rfp_tracing_log (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id uuid NOT NULL REFERENCES public.rfp_tickets(id) ON DELETE CASCADE,
    department text,
    node_name text NOT NULL,
    agent text NOT NULL,
    input_preview text NOT NULL DEFAULT '',
    output_preview text NOT NULL DEFAULT '',
    full_input jsonb DEFAULT '{}'::jsonb,
    full_output jsonb DEFAULT '{}'::jsonb,
    run_id text NOT NULL DEFAULT '',
    timestamp timestamptz NOT NULL DEFAULT now()
);

-- Arbitration records
CREATE TABLE public.rfp_arbitration_records (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id uuid NOT NULL REFERENCES public.rfp_tickets(id) ON DELETE CASCADE,
    conflict_id text NOT NULL,
    departments_involved text[] NOT NULL DEFAULT '{}',
    description text NOT NULL DEFAULT '',
    resolved_by text NOT NULL DEFAULT 'Mariana Restrepo',
    resolution text NOT NULL DEFAULT '',
    timestamp timestamptz NOT NULL DEFAULT now(),
    run_id text NOT NULL DEFAULT ''
);

CREATE INDEX rfp_approval_status_ticket_idx ON public.rfp_approval_status (ticket_id);
CREATE INDEX rfp_tracing_log_ticket_idx ON public.rfp_tracing_log (ticket_id, run_id);
CREATE INDEX rfp_arbitration_ticket_idx ON public.rfp_arbitration_records (ticket_id);

ALTER TABLE public.rfp_approval_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rfp_final_document ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rfp_tracing_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rfp_arbitration_records ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.rfp_approval_status, public.rfp_final_document,
    public.rfp_tracing_log, public.rfp_arbitration_records
    FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.rfp_approval_status,
    public.rfp_final_document, public.rfp_tracing_log,
    public.rfp_arbitration_records TO service_role;

GRANT USAGE, SELECT ON SEQUENCE public.rfp_approval_status_id_seq,
    public.rfp_final_document_id_seq, public.rfp_tracing_log_id_seq,
    public.rfp_arbitration_records_id_seq TO service_role;

COMMIT;