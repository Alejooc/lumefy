"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  getStorefrontAccountMe,
  resolveStorefront,
} from "@/lib/storefront-api";
import { PublicStorefrontAccountUser } from "@/types/storefront";

type StorefrontSession = {
  token: string;
  storefrontId: string;
  user: PublicStorefrontAccountUser;
};

type StorefrontAuthContextValue = {
  session: StorefrontSession | null;
  loading: boolean;
  signIn: (session: StorefrontSession) => void;
  refreshSession: () => Promise<void>;
  signOut: () => void;
};

const STORAGE_KEY = "nextmerce-storefront-session";

const StorefrontAuthContext = createContext<StorefrontAuthContextValue | null>(null);

function readStoredSession(): StorefrontSession | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as StorefrontSession;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function writeStoredSession(session: StorefrontSession | null) {
  if (typeof window === "undefined") {
    return;
  }

  if (!session) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function StorefrontAuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<StorefrontSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function hydrate() {
      const stored = readStoredSession();
      if (!stored) {
        if (active) {
          setLoading(false);
        }
        return;
      }

      try {
        const me = await getStorefrontAccountMe(stored.storefrontId, stored.token);
        if (!active) {
          return;
        }
        const nextSession = { ...stored, user: me };
        setSession(nextSession);
        writeStoredSession(nextSession);
      } catch {
        writeStoredSession(null);
        if (active) {
          setSession(null);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    hydrate();

    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<StorefrontAuthContextValue>(
    () => ({
      session,
      loading,
      signIn(nextSession) {
        setSession(nextSession);
        writeStoredSession(nextSession);
      },
      async refreshSession() {
        const stored = readStoredSession();
        if (!stored) {
          setSession(null);
          return;
        }
        const storefront = await resolveStorefront();
        const me = await getStorefrontAccountMe(storefront.id, stored.token);
        const nextSession = {
          token: stored.token,
          storefrontId: storefront.id,
          user: me,
        };
        setSession(nextSession);
        writeStoredSession(nextSession);
      },
      signOut() {
        setSession(null);
        writeStoredSession(null);
      },
    }),
    [loading, session],
  );

  return (
    <StorefrontAuthContext.Provider value={value}>
      {children}
    </StorefrontAuthContext.Provider>
  );
}

export function useStorefrontAuth() {
  const context = useContext(StorefrontAuthContext);
  if (!context) {
    throw new Error("useStorefrontAuth must be used within StorefrontAuthProvider");
  }
  return context;
}
