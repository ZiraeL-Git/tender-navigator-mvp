"use client";

export const SESSION_KEY = "tn_operator_session";
export const ACTIVE_PROFILE_KEY = "tn_active_profile_id";

export type OperatorSession = {
  name: string;
  email: string;
};

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(key);
}

export function readSession(): OperatorSession | null {
  const value = readLocalStorage(SESSION_KEY);
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value) as OperatorSession;
  } catch {
    return null;
  }
}

export function saveSession(session: OperatorSession): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(SESSION_KEY);
  window.localStorage.removeItem(ACTIVE_PROFILE_KEY);
}

export function readActiveProfileId(): number | null {
  const value = readLocalStorage(ACTIVE_PROFILE_KEY);
  if (!value) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function saveActiveProfileId(profileId: number): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(ACTIVE_PROFILE_KEY, String(profileId));
}
