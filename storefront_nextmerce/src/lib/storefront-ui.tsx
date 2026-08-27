"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import type { PublicStorefront } from "@/types/storefront";
import {
  getStorefrontBranding,
  getStorefrontButtonLabelsFromSettings,
  type StorefrontButtonLabels,
} from "@/lib/storefront-branding";
import { isTrustedPreviewMessage } from "@/lib/preview";

type StorefrontUiContextValue = {
  buttonLabels: StorefrontButtonLabels;
};

const StorefrontUiContext = createContext<StorefrontUiContextValue | null>(null);

export function StorefrontUiProvider({
  children,
  initialStorefront,
}: {
  children: ReactNode;
  initialStorefront: PublicStorefront;
}) {
  const initialLabels = useMemo(
    () => getStorefrontBranding(initialStorefront).buttonLabels,
    [initialStorefront],
  );
  const [buttonLabels, setButtonLabels] = useState<StorefrontButtonLabels>(initialLabels);

  useEffect(() => {
    setButtonLabels(initialLabels);
  }, [initialLabels]);

  useEffect(() => {
    const handlePreviewMessage = (event: MessageEvent) => {
      if (!isTrustedPreviewMessage(event)) return;
      const message = event.data;
      if (!message || message.type !== "lumefy:preview:apply" || message.template !== "home") return;

      const document = message.document && typeof message.document === "object"
        ? message.document as Record<string, unknown>
        : {};
      const settings = document["settings"] && typeof document["settings"] === "object"
        ? document["settings"]
        : {};
      setButtonLabels(getStorefrontButtonLabelsFromSettings(settings));
    };

    window.addEventListener("message", handlePreviewMessage);
    return () => window.removeEventListener("message", handlePreviewMessage);
  }, []);

  const value = useMemo(() => ({ buttonLabels }), [buttonLabels]);

  return <StorefrontUiContext.Provider value={value}>{children}</StorefrontUiContext.Provider>;
}

export function useStorefrontUi(): StorefrontUiContextValue {
  const context = useContext(StorefrontUiContext);
  if (!context) {
    throw new Error("useStorefrontUi debe usarse dentro de StorefrontUiProvider");
  }
  return context;
}
