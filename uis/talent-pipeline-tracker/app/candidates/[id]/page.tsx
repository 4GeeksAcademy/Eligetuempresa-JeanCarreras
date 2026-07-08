"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Toast } from "../../../components/Toast";
import {
  addNoteToRecord,
  deleteNoteFromRecord,
  deleteRecordById,
  getNotesByRecordId,
  getRecordById,
  patchRecordById,
  putRecordById,
} from "../../../services/trackerApi";
import {
  STAGE_LABELS,
  STAGE_OPTIONS,
  STATUS_LABELS,
  STATUS_OPTIONS,
  type CandidateRecord,
  type Note,
  type RecordCreatePayload,
  type ToastTone,
} from "../../../types/tracker";

function fmtDateTime(dateRaw: string): string {
  const date = new Date(dateRaw);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return date.toLocaleString("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();

  const id = params.id;

  const [candidate, setCandidate] = useState<CandidateRecord | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [isPatching, setIsPatching] = useState(false);
  const [isSavingCandidate, setIsSavingCandidate] = useState(false);
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [deletingNoteId, setDeletingNoteId] = useState<string | null>(null);
  const [isDeletingCandidate, setIsDeletingCandidate] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const [errorMessage, setErrorMessage] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [actionTone, setActionTone] = useState<ToastTone>("info");
  const [toastMessage, setToastMessage] = useState("");
  const [toastTone, setToastTone] = useState<ToastTone>("info");

  const [editForm, setEditForm] = useState<RecordCreatePayload>({
    full_name: "",
    email: "",
    phone: "",
    position: "",
    linkedin_url: null,
    cv_url: null,
    experience_years: 0,
  });
  const [newNote, setNewNote] = useState("");

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

  const loadDetail = useCallback(async () => {
    setErrorMessage("");

    try {
      const [record, notesPayload] = await Promise.all([
        getRecordById(id),
        getNotesByRecordId(id),
      ]);

      setCandidate({
        ...record,
        notes_count: record.notes_count ?? notesPayload.length,
      });
      setNotes(notesPayload);

      setEditForm({
        full_name: record.full_name,
        email: record.email,
        phone: record.phone,
        position: record.position,
        linkedin_url: record.linkedin_url,
        cv_url: record.cv_url,
        experience_years: record.experience_years,
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Error cargando candidatura");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let ignore = false;

    async function run() {
      await loadDetail();
      if (ignore) {
        return;
      }
    }

    run();

    return () => {
      ignore = true;
    };
  }, [loadDetail]);

  const statusOptions = Array.from(
    new Set([...STATUS_OPTIONS, ...(candidate?.status ? [candidate.status] : [])])
  );

  const stageOptions = Array.from(
    new Set([...STAGE_OPTIONS, ...(candidate?.stage ? [candidate.stage] : [])])
  );

  const fromQuery = searchParams.get("from");
  const backHref = fromQuery ? `/?${fromQuery}` : "/";

  const patchCandidate = async (patch: { status?: string; stage?: string }) => {
    if (!candidate) {
      return;
    }

    setActionMessage("");
    setActionTone("info");
    setIsPatching(true);

    try {
      const patched = await patchRecordById(id, patch);

      setCandidate((current) =>
        current
          ? {
              ...current,
              ...patched,
            }
          : patched
      );
      setActionMessage("Estado de candidatura actualizado.");
      setActionTone("success");
      openToast("Estado/etapa actualizados", "success");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "No se pudo actualizar estado/etapa");
      setActionTone("error");
      openToast("No se pudo actualizar estado/etapa", "error");
    } finally {
      setIsPatching(false);
    }
  };

  const saveCandidate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setActionMessage("");
    setActionTone("info");
    setIsSavingCandidate(true);

    try {
      const payload: RecordCreatePayload = {
        ...editForm,
        full_name: editForm.full_name.trim(),
        email: editForm.email.trim(),
        phone: editForm.phone.trim(),
        position: editForm.position.trim(),
        linkedin_url: editForm.linkedin_url?.trim() ? editForm.linkedin_url.trim() : null,
        cv_url: editForm.cv_url?.trim() ? editForm.cv_url.trim() : null,
      };

      const updated = await putRecordById(id, payload);

      setCandidate((current) =>
        current
          ? {
              ...current,
              ...updated,
            }
          : updated
      );
      setActionMessage("Datos de candidatura guardados.");
      setActionTone("success");
      openToast("Datos guardados", "success");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "No se pudo guardar la candidatura");
      setActionTone("error");
      openToast("No se pudo guardar la candidatura", "error");
    } finally {
      setIsSavingCandidate(false);
    }
  };

  const addNote = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const content = newNote.trim();
    if (!content) {
      return;
    }

    setActionMessage("");
    setActionTone("info");
    setIsAddingNote(true);

    try {
      const note = await addNoteToRecord(id, content);

      setNotes((current) => [note, ...current]);
      setCandidate((current) =>
        current
          ? {
              ...current,
              notes_count: current.notes_count + 1,
            }
          : current
      );
      setNewNote("");
      setActionMessage("Nota agregada.");
      setActionTone("success");
      openToast("Nota agregada", "success");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "No se pudo agregar la nota");
      setActionTone("error");
      openToast("No se pudo agregar la nota", "error");
    } finally {
      setIsAddingNote(false);
    }
  };

  const deleteNote = async (noteId: string) => {
    setActionMessage("");
    setActionTone("info");
    setDeletingNoteId(noteId);

    try {
      await deleteNoteFromRecord(id, noteId);

      setNotes((current) => current.filter((note) => note.id !== noteId));
      setCandidate((current) =>
        current
          ? {
              ...current,
              notes_count: Math.max(0, current.notes_count - 1),
            }
          : current
      );
      setActionMessage("Nota eliminada.");
      setActionTone("success");
      openToast("Nota eliminada", "success");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "No se pudo eliminar la nota");
      setActionTone("error");
      openToast("No se pudo eliminar la nota", "error");
    } finally {
      setDeletingNoteId(null);
    }
  };

  const deleteCandidate = async () => {
    setIsDeletingCandidate(true);
    setActionMessage("");

    try {
      await deleteRecordById(id);
      setIsDeleteModalOpen(false);
      openToast("Candidatura eliminada", "success");
      router.push(backHref);
    } catch (error) {
      const message = error instanceof Error ? error.message : "No se pudo eliminar la candidatura";
      setActionMessage(message);
      setActionTone("error");
      openToast("No se pudo eliminar la candidatura", "error");
    } finally {
      setIsDeletingCandidate(false);
    }
  };

  if (isLoading) {
    return (
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-4 py-8 sm:px-6 lg:px-10">
        <section className="rounded-2xl border bg-white p-6 text-[var(--muted)] shadow-sm">
          Cargando candidatura...
        </section>
      </main>
    );
  }

  if (errorMessage || !candidate) {
    return (
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-4 py-8 sm:px-6 lg:px-10">
        <section className="rounded-2xl border bg-white p-6 text-[var(--brand-2)] shadow-sm">
          <p className="feedback feedback-error">Error cargando candidatura: {errorMessage || "No se encontro el registro"}</p>
        </section>
        <Link href={backHref} className="rounded-lg border bg-white px-3 py-2 text-sm font-semibold w-fit">
          Volver al listado
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-4 py-8 sm:px-6 lg:px-10">
      <header className="flex items-center justify-between gap-3 rounded-2xl border bg-[var(--surface-strong)] p-6 shadow-[0_20px_60px_-40px_rgba(26,31,54,0.5)]">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--brand)]">
            Personas y Cultura | Brasaland
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            Ficha de candidatura: {candidate.full_name}
          </h1>
          <p className="mt-1 text-sm text-[var(--muted)]">{candidate.position} | Sede: Colombia / Florida</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsDeleteModalOpen(true)}
            disabled={isDeletingCandidate}
            className="rounded-lg border border-[#ffc9b8] bg-[#fff1ec] px-3 py-2 text-sm font-semibold text-[#b8401f] transition hover:bg-[#ffdccc] disabled:opacity-50"
          >
            {isDeletingCandidate ? "Eliminando..." : "Eliminar candidatura"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-lg border bg-white px-3 py-2 text-sm font-semibold transition hover:bg-[var(--surface)]"
          >
            Atras
          </button>
          <Link
            href={backHref}
            className="rounded-lg border bg-white px-3 py-2 text-sm font-semibold transition hover:bg-[var(--surface)]"
          >
            Ir al listado
          </Link>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-4 rounded-2xl border bg-white p-6 shadow-sm md:grid-cols-2">
        <article>
          <p className="text-xs uppercase tracking-wide text-[var(--muted)]">Estado</p>
          <select
            disabled={isPatching}
            value={candidate.status}
            onChange={(event) => patchCandidate({ status: event.target.value })}
            className="mt-1 w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)] disabled:opacity-50"
          >
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {STATUS_LABELS[status] ?? status}
              </option>
            ))}
          </select>
        </article>

        <article>
          <p className="text-xs uppercase tracking-wide text-[var(--muted)]">Etapa</p>
          <select
            disabled={isPatching}
            value={candidate.stage}
            onChange={(event) => patchCandidate({ stage: event.target.value })}
            className="mt-1 w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)] disabled:opacity-50"
          >
            {stageOptions.map((stage) => (
              <option key={stage} value={stage}>
                {STAGE_LABELS[stage] ?? stage}
              </option>
            ))}
          </select>
        </article>

        <article>
          <p className="text-xs uppercase tracking-wide text-[var(--muted)]">Fecha de postulacion</p>
          <p className="mt-1 text-sm font-semibold">{fmtDateTime(candidate.applied_at)}</p>
        </article>

        <article>
          <p className="text-xs uppercase tracking-wide text-[var(--muted)]">Ultima actualizacion</p>
          <p className="mt-1 text-sm font-semibold">{fmtDateTime(candidate.updated_at)}</p>
        </article>
      </section>

      <section className="rounded-2xl border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Editar candidatura</h2>
        <form onSubmit={saveCandidate} className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          <label>
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Nombre completo</span>
            <input
              required
              value={editForm.full_name}
              onChange={(event) => setEditForm((c) => ({ ...c, full_name: event.target.value }))}
              className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
            />
          </label>

          <label>
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Puesto</span>
            <input
              required
              value={editForm.position}
              onChange={(event) => setEditForm((c) => ({ ...c, position: event.target.value }))}
              className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
            />
          </label>

          <label>
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Email</span>
            <input
              type="email"
              required
              value={editForm.email}
              onChange={(event) => setEditForm((c) => ({ ...c, email: event.target.value }))}
              className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
            />
          </label>

          <label>
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Telefono</span>
            <input
              required
              value={editForm.phone}
              onChange={(event) => setEditForm((c) => ({ ...c, phone: event.target.value }))}
              className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
            />
          </label>

          <label>
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">LinkedIn</span>
            <input
              type="url"
              value={editForm.linkedin_url ?? ""}
              onChange={(event) => setEditForm((c) => ({ ...c, linkedin_url: event.target.value || null }))}
              className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
            />
          </label>

          <label>
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">CV URL</span>
            <input
              type="url"
              value={editForm.cv_url ?? ""}
              onChange={(event) => setEditForm((c) => ({ ...c, cv_url: event.target.value || null }))}
              className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
            />
          </label>

          <label>
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]">Experiencia (anos)</span>
            <input
              type="number"
              min={0}
              required
              value={editForm.experience_years}
              onChange={(event) =>
                setEditForm((c) => ({ ...c, experience_years: Number(event.target.value) }))
              }
              className="w-full rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
            />
          </label>

          <div className="md:col-span-2 flex items-center gap-3">
            <button
              type="submit"
              disabled={isSavingCandidate}
              className="rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
            >
              {isSavingCandidate ? "Guardando..." : "Guardar cambios"}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Notas internas</h2>

        <form onSubmit={addNote} className="mt-4 flex flex-col gap-3">
          <textarea
            value={newNote}
            onChange={(event) => setNewNote(event.target.value)}
            placeholder="Escribe una nota para el equipo"
            className="min-h-24 rounded-lg border px-3 py-2 outline-none transition focus:border-[var(--brand)]"
          />
          <div>
            <button
              type="submit"
              disabled={isAddingNote}
              className="rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
            >
              {isAddingNote ? "Agregando..." : "Agregar nota"}
            </button>
          </div>
        </form>

        <div className="mt-4 space-y-3">
          {notes.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">No hay notas para esta candidatura.</p>
          ) : (
            notes.map((note) => (
              <article key={note.id} className="rounded-lg border p-3">
                <p className="text-sm whitespace-pre-wrap">{note.content}</p>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <span className="text-xs text-[var(--muted)]">{fmtDateTime(note.created_at)}</span>
                  <button
                    type="button"
                    disabled={deletingNoteId === note.id}
                    onClick={() => deleteNote(note.id)}
                    className="rounded-md border px-2 py-1 text-xs font-semibold text-[var(--brand-2)] transition hover:bg-[var(--surface)] disabled:opacity-50"
                  >
                    {deletingNoteId === note.id ? "Eliminando..." : "Eliminar"}
                  </button>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      {actionMessage ? (
        <section className="rounded-xl border bg-white px-4 py-3 shadow-sm">
          <p className={`feedback ${actionTone === "success" ? "feedback-success" : actionTone === "error" ? "feedback-error" : "feedback-info"}`}>
            {actionMessage}
          </p>
        </section>
      ) : null}

      <Toast message={toastMessage} tone={toastTone} />

      {isDeleteModalOpen ? (
        <section className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Confirmar eliminacion">
          <article className="modal-card">
            <h3 className="text-lg font-semibold">Confirmar eliminacion</h3>
            <p className="mt-2 text-sm text-[var(--muted)]">
              Esta accion eliminara de forma permanente la candidatura y no se puede deshacer.
            </p>

            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsDeleteModalOpen(false)}
                disabled={isDeletingCandidate}
                className="rounded-lg border bg-white px-3 py-2 text-sm font-semibold transition hover:bg-[var(--surface)] disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={deleteCandidate}
                disabled={isDeletingCandidate}
                className="rounded-lg border border-[#ffc9b8] bg-[#fff1ec] px-3 py-2 text-sm font-semibold text-[#b8401f] transition hover:bg-[#ffdccc] disabled:opacity-50"
              >
                {isDeletingCandidate ? "Eliminando..." : "Si, eliminar"}
              </button>
            </div>
          </article>
        </section>
      ) : null}
    </main>
  );
}
