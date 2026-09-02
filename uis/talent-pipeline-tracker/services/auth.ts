"use client";

export const ACCESS_TOKEN_KEY = "brasaland_access_token";
export const AUTH_UNAUTHORIZED_EVENT = "brasaland:unauthorized";

export type UserProfile = {
  email: string;
  name?: string | null;
  phone?: string | null;
  address?: string | null;
};

export function getAccessToken(): string | null {
  return typeof window === "undefined" ? null : window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function saveAccessToken(token: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearSession(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function notifyUnauthorized(): void {
  clearSession();
  window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
}