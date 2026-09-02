import { getAccessToken, notifyUnauthorized, type UserProfile } from "./auth";

type LoginResponse = {
  access_token?: string;
  token?: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  name?: string;
  phone?: string;
  address?: string;
};

function getApiBase(): string {
  const apiBase = process.env.NEXT_PUBLIC_API_URL;
  if (!apiBase) {
    throw new Error("NEXT_PUBLIC_API_URL no esta configurada");
  }

  return apiBase.replace(/\/$/, "");
}

async function getErrorMessage(response: Response): Promise<string> {
  const fallback = `Error ${response.status}. Intenta de nuevo.`;

  try {
    const body = (await response.json()) as { detail?: unknown; message?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (typeof body.message === "string") {
      return body.message;
    }
  } catch {
    return fallback;
  }

  return fallback;
}

async function requestAuth<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<string> {
  const response = await requestAuth<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  const token = response.access_token ?? response.token;

  if (!token) {
    throw new Error("La API no devolvio un token de acceso.");
  }

  return token;
}

export async function register(payload: RegisterPayload): Promise<void> {
  await requestAuth<unknown>("/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCurrentProfile(): Promise<UserProfile> {
  return await protectedRequest<UserProfile>("/auth/me");
}

export async function updateCurrentProfile(profile: Omit<UserProfile, "email">): Promise<UserProfile> {
  return await protectedRequest<UserProfile>("/profiles/me", {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

export async function protectedRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  return await protectedRequestUrl<T>(`${getApiBase()}${path}`, init);
}

export async function protectedRequestUrl<T>(url: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) {
    notifyUnauthorized();
    throw new Error("La sesion ha terminado. Inicia sesion nuevamente.");
  }

  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });

  if (response.status === 401) {
    notifyUnauthorized();
    throw new Error("La sesion ha terminado. Inicia sesion nuevamente.");
  }

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return (await response.json()) as T;
}

export async function protectedRequestNoContent(path: string, init: RequestInit = {}): Promise<void> {
  await protectedRequestNoContentUrl(`${getApiBase()}${path}`, init);
}

export async function protectedRequestNoContentUrl(url: string, init: RequestInit = {}): Promise<void> {
  const token = getAccessToken();
  if (!token) {
    notifyUnauthorized();
    throw new Error("La sesion ha terminado. Inicia sesion nuevamente.");
  }

  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });

  if (response.status === 401) {
    notifyUnauthorized();
    throw new Error("La sesion ha terminado. Inicia sesion nuevamente.");
  }

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }
}