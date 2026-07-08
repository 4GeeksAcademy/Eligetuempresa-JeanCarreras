import type {
  CandidateApiRecord,
  CandidateRecord,
  Note,
  RecordCreatePayload,
  RecordsApiResponse,
} from "../types/tracker";

function getApiBase(): string {
  const apiBase = process.env.NEXT_PUBLIC_API_URL;
  if (!apiBase) {
    throw new Error("NEXT_PUBLIC_API_URL no esta configurada");
  }

  return apiBase;
}

function normalizeRecord(record: CandidateApiRecord): CandidateRecord {
  return {
    ...record,
    notes_count: record.notes_count ?? record.notes?.length ?? 0,
  };
}

function normalizeNotes(payload: unknown): Note[] {
  if (Array.isArray(payload)) {
    return payload as Note[];
  }

  if (payload && typeof payload === "object" && "data" in payload) {
    const maybeData = (payload as { data?: unknown }).data;
    if (Array.isArray(maybeData)) {
      return maybeData as Note[];
    }
  }

  return [];
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Error ${response.status} en ${url}`);
  }

  return (await response.json()) as T;
}

async function requestNoContent(url: string, init?: RequestInit): Promise<void> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`Error ${response.status} en ${url}`);
  }
}

async function fetchRecordsPage(page: number, limit: number): Promise<RecordsApiResponse> {
  const apiBase = getApiBase();
  const url = new URL(`${apiBase}/records`);
  url.searchParams.set("page", String(page));
  url.searchParams.set("limit", String(limit));

  const payload = (await requestJson<RecordsApiResponse | CandidateApiRecord[]>(url.toString())) as
    | RecordsApiResponse
    | CandidateApiRecord[];

  if (Array.isArray(payload)) {
    return {
      data: payload,
      total: payload.length,
      page: 1,
      limit: payload.length,
    };
  }

  return payload;
}

export async function fetchAllRecords(): Promise<CandidateRecord[]> {
  const limit = 50;
  const firstPage = await fetchRecordsPage(1, limit);
  const firstData = firstPage.data ?? [];
  const total = firstPage.total ?? firstData.length;

  const all = [...firstData];
  let page = 2;

  while (all.length < total) {
    const nextPage = await fetchRecordsPage(page, limit);
    const pageData = nextPage.data ?? [];
    if (pageData.length === 0) {
      break;
    }

    all.push(...pageData);
    page += 1;
  }

  return all.map(normalizeRecord);
}

export async function createRecord(payload: RecordCreatePayload): Promise<CandidateRecord> {
  const apiBase = getApiBase();
  const created = await requestJson<CandidateApiRecord>(`${apiBase}/records`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return normalizeRecord(created);
}

export async function getRecordById(id: string): Promise<CandidateRecord> {
  const apiBase = getApiBase();
  return await requestJson<CandidateRecord>(`${apiBase}/records/${id}`);
}

export async function patchRecordById(
  id: string,
  patch: { status?: string; stage?: string }
): Promise<CandidateRecord> {
  const apiBase = getApiBase();
  return await requestJson<CandidateRecord>(`${apiBase}/records/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
}

export async function putRecordById(
  id: string,
  payload: RecordCreatePayload
): Promise<CandidateRecord> {
  const apiBase = getApiBase();
  return await requestJson<CandidateRecord>(`${apiBase}/records/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteRecordById(id: string): Promise<void> {
  const apiBase = getApiBase();
  await requestNoContent(`${apiBase}/records/${id}`, { method: "DELETE" });
}

export async function getNotesByRecordId(id: string): Promise<Note[]> {
  const apiBase = getApiBase();
  const payload = await requestJson<unknown>(`${apiBase}/records/${id}/notes`);
  return normalizeNotes(payload);
}

export async function addNoteToRecord(id: string, content: string): Promise<Note> {
  const apiBase = getApiBase();
  return await requestJson<Note>(`${apiBase}/records/${id}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}

export async function deleteNoteFromRecord(id: string, noteId: string): Promise<void> {
  const apiBase = getApiBase();
  await requestNoContent(`${apiBase}/records/${id}/notes/${noteId}`, {
    method: "DELETE",
  });
}
