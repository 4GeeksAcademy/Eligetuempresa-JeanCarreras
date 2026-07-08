"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Toast } from "../components/Toast";
import { createRecord, fetchAllRecords } from "../services/trackerApi";
import {
  DEFAULT_STAGES,
  DEFAULT_STATUSES,
  EMPTY_CREATE_FORM,
  STAGE_LABELS,
  STATUS_LABELS,
  type CandidateRecord,
  type RecordCreatePayload,
  type ToastTone,
} from "../types/tracker";

export default function Home() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [records, setRecords] = useState<CandidateRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createSuccess, setCreateSuccess] = useState("");
  const [createInfo, setCreateInfo] = useState("Completa los campos requeridos antes de enviar.");
  const [createForm, setCreateForm] = useState<RecordCreatePayload>(EMPTY_CREATE_FORM);
  const [toastMessage, setToastMessage] = useState("");
  const [toastTone, setToastTone] = useState<ToastTone>("info");

  const qParam = searchParams.get("q") ?? "";
  const statusParam = (searchParams.get("status") ?? "all").toLowerCase();
  const stageParam = (searchParams.get("stage") ?? "all").toLowerCase();
  const searchDebounceRef = useRef<number | null>(null);

  const openToast = useCallback((message: string, tone: ToastTone) => {
    setToastMessage(message);
    setToastTone(tone);
  }, []);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }

    const timeoutId = window.setTimeout(() => setToastMessage(""), 3200);
    return () => clearTimeout(timeoutId);
  }, [toastMessage]);

  const loadRecords = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");

    try {
      const data = await fetchAllRecords();
      setRecords(data);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Error desconocido cargando candidaturas"
      );
      openToast("Error consultando candidaturas", "error");
    } finally {
      setIsLoading(false);
    }
  }, [openToast]);

  useEffect(() => {
    let ignore = false;

    async function load() {
      await loadRecords();
      if (ignore) {
        return;
      }
    }

    load();

    return () => {
      ignore = true;
    };
  }, [loadRecords]);

  const updateParam = useCallback((key: string, value: string) => {
    const next = new URLSearchParams(searchParams.toString());

    if (!value || value === "all") {
      next.delete(key);
    } else {
      next.set(key, value);
    }

    const queryString = next.toString();
    router.replace(queryString ? `${pathname}?${queryString}` : pathname, {
      scroll: false,
    });
  }, [pathname, router, searchParams]);

  const onSearchChange = (value: string) => {
    if (searchDebounceRef.current !== null) {
      clearTimeout(searchDebounceRef.current);
    }

    searchDebounceRef.current = window.setTimeout(() => {
      updateParam("q", value.trim());
    }, 250);
  };

  const onCreateFieldChange = (key: keyof RecordCreatePayload, value: string | number | null) => {
    setCreateForm((current) => ({ ...current, [key]: value }));
  };

  const onCreateSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreateError("");
    setCreateSuccess("");
    setCreateInfo("");
    setIsCreating(true);

    try {
      const payload: RecordCreatePayload = {
        ...createForm,
        full_name: createForm.full_name.trim(),
        email: createForm.email.trim(),
        phone: createForm.phone.trim(),
        position: createForm.position.trim(),
        linkedin_url: createForm.linkedin_url?.trim() ? createForm.linkedin_url.trim() : null,
        cv_url: createForm.cv_url?.trim() ? createForm.cv_url.trim() : null,
      };

      await createRecord(payload);
      setCreateSuccess("Candidatura registrada correctamente.");
      openToast("Candidatura creada correctamente", "success");
      setCreateInfo("");
      setCreateForm(EMPTY_CREATE_FORM);
      await loadRecords();
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "No se pudo registrar la candidatura");
      openToast("No se pudo crear la candidatura", "error");
      setCreateInfo("");
    } finally {
      setIsCreating(false);
    }
  };

  const filteredRecords = useMemo(() => {
    const q = qParam.trim().toLowerCase();

    return records.filter((record) => {
      const matchesQuery =
        q.length === 0 ||
        record.full_name.toLowerCase().includes(q) ||
        record.email.toLowerCase().includes(q);
      const matchesStatus = statusParam === "all" || record.status.toLowerCase() === statusParam;
      const matchesStage = stageParam === "all" || record.stage.toLowerCase() === stageParam;

      return matchesQuery && matchesStatus && matchesStage;
    });
  }, [records, qParam, statusParam, stageParam]);

  const knownStatuses = useMemo(
    () => Array.from(new Set([...DEFAULT_STATUSES, ...records.map((record) => record.status)])).sort((a, b) => a.localeCompare(b)),
    [records]
  );

  const knownStages = useMemo(
    () => Array.from(new Set([...DEFAULT_STAGES, ...records.map((record) => record.stage)])).sort((a, b) => a.localeCompare(b)),
    [records]
  );

  const listContext = searchParams.toString();

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-8 sm:px-6 lg:px-10">
      <header className="rounded-2xl border bg-[var(--surface-strong)] p-6 shadow-[0_20px_60px_-40px_rgba(26,31,54,0.5)]">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--brand)]">
          Personas y Cultura | Brasaland
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          Pipeline de candidaturas
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)] sm:text-base">
          Seguimiento interno para sedes de Colombia y Florida, con foco en cobertura operativa de vacantes.
        </p>
      </header>

      <section className="rounded-2xl border bg-white p-4 shadow-sm sm:p-6">
        <div className="mb-4 flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Filtros</h2>
          <button
            type="button"
            onClick={() => {
              setShowCreateForm((current) => !current);
              setCreateError("");
              setCreateSuccess("");
              setCreateInfo("Completa los campos requeridos antes de enviar.");
            }}
            className="rounded-lg bg-[var(--brand)] px-3 py-2 text-sm font-semibold text-white transition hover:opacity-90"
          >
            {showCreateForm ? "Cerrar formulario" : "Nueva postulacion"}
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <label className="md:col-span-2">
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Buscar por nombre o correo
            </span>
            <input
              key={qParam}
              defaultValue={qParam}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Escribe para filtrar"
              className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
            />
          </label>

          <label>
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Estado
            </span>
            <select
              value={statusParam}
              onChange={(event) => updateParam("status", event.target.value)}
              className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
            >
              <option value="all">Todos</option>
              {knownStatuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Etapa
            </span>
            <select
              value={stageParam}
              onChange={(event) => updateParam("stage", event.target.value)}
              className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
            >
              <option value="all">Todas</option>
              {knownStages.map((stage) => (
                <option key={stage} value={stage}>
                  {STAGE_LABELS[stage] ?? stage}
                </option>
              ))}
            </select>
          </label>
        </div>

        {showCreateForm ? (
          <form onSubmit={onCreateSubmit} className="mt-6 grid grid-cols-1 gap-3 rounded-xl border p-4 md:grid-cols-2">
            <h3 className="md:col-span-2 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
              Registrar postulacion
            </h3>

            <label>
              <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Nombre completo</span>
              <input
                required
                value={createForm.full_name}
                onChange={(event) => onCreateFieldChange("full_name", event.target.value)}
                className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Puesto</span>
              <input
                required
                value={createForm.position}
                onChange={(event) => onCreateFieldChange("position", event.target.value)}
                className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Email</span>
              <input
                required
                type="email"
                value={createForm.email}
                onChange={(event) => onCreateFieldChange("email", event.target.value)}
                className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Telefono</span>
              <input
                required
                value={createForm.phone}
                onChange={(event) => onCreateFieldChange("phone", event.target.value)}
                className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">LinkedIn</span>
              <input
                type="url"
                value={createForm.linkedin_url ?? ""}
                onChange={(event) => onCreateFieldChange("linkedin_url", event.target.value)}
                className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">CV URL</span>
              <input
                type="url"
                value={createForm.cv_url ?? ""}
                onChange={(event) => onCreateFieldChange("cv_url", event.target.value)}
                className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
              />
            </label>

            <label>
              <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Experiencia (anos)</span>
              <input
                required
                min={0}
                type="number"
                value={createForm.experience_years}
                onChange={(event) => onCreateFieldChange("experience_years", Number(event.target.value))}
                className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
              />
            </label>

            <div className="md:col-span-2 flex items-center gap-3">
              <button
                type="submit"
                disabled={isCreating}
                className="rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isCreating ? "Guardando..." : "Registrar postulacion"}
              </button>
            </div>

            {createInfo ? <p className="feedback feedback-info md:col-span-2">{createInfo}</p> : null}
            {createSuccess ? <p className="feedback feedback-success md:col-span-2">{createSuccess}</p> : null}
            {createError ? <p className="feedback feedback-error md:col-span-2">{createError}</p> : null}
          </form>
        ) : null}
      </section>

      <section className="overflow-hidden rounded-2xl border bg-white shadow-sm">
        {isLoading ? (
          <div className="px-4 py-6">
            <p className="feedback feedback-info">Cargando candidaturas...</p>
          </div>
        ) : errorMessage ? (
          <div className="px-4 py-6">
            <p className="feedback feedback-error">Error cargando datos: {errorMessage}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-[var(--surface)] text-left font-mono text-xs uppercase tracking-wide text-[var(--muted)]">
                <tr>
                  <th className="px-4 py-3">Nombre</th>
                  <th className="px-4 py-3">Rol solicitado</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3">Etapa</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-10 text-center text-[var(--muted)]">
                      No hay postulaciones para los filtros actuales.
                    </td>
                  </tr>
                ) : (
                  filteredRecords.map((record) => (
                    <tr key={record.id} className="border-t">
                      <td className="px-4 py-3">
                        <Link
                          href={`/candidates/${record.id}${listContext ? `?from=${encodeURIComponent(listContext)}` : ""}`}
                          className="font-semibold hover:text-[var(--brand)]"
                        >
                          {record.full_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3">{record.position}</td>
                      <td className="px-4 py-3">{STATUS_LABELS[record.status] ?? record.status}</td>
                      <td className="px-4 py-3">{STAGE_LABELS[record.stage] ?? record.stage}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Toast message={toastMessage} tone={toastTone} />
    </main>
  );
}
