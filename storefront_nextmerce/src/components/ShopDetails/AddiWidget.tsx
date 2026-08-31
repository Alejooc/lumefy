"use client";

import React, { useEffect, useState } from "react";
import Script from "next/script";

const ADDI_WIDGET_SCRIPT = "https://s3.amazonaws.com/widgets.addi.com/bundle.min.js";

export type AddiWidgetConfig = {
  allySlug: string;
  isSandbox?: boolean;
};

function AddiMark() {
  return (
    <span
      aria-hidden="true"
      className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#f5c84c] text-sm font-bold text-[#1f2937]"
    >
      A
    </span>
  );
}

export default function AddiWidget({ price, config }: { price: number; config: AddiWidgetConfig }) {
  const [scriptReady, setScriptReady] = useState(false);
  const normalizedPrice = Math.max(0, Math.round(Number(price) || 0));
  const allySlug = config.allySlug.trim();

  useEffect(() => {
    if (typeof window === "undefined" || !allySlug || normalizedPrice <= 0) return;

    if (window.customElements?.get("addi-widget")) {
      setScriptReady(true);
      return;
    }

    let mounted = true;
    window.customElements?.whenDefined("addi-widget").then(() => {
      if (mounted) setScriptReady(true);
    });

    return () => {
      mounted = false;
    };
  }, [allySlug, normalizedPrice]);

  if (!allySlug || normalizedPrice <= 0) return null;

  const widget = React.createElement("addi-widget", {
    key: `${allySlug}-${normalizedPrice}`,
    price: String(normalizedPrice),
    "ally-slug": allySlug,
  });

  return (
    <section
      aria-label="Opciones de financiación con Addi"
      className="mb-6 rounded-xl border border-[#eadfbf] bg-[#fffaf0] p-4 sm:p-5"
    >
      <Script
        id="addi-widget-script"
        src={ADDI_WIDGET_SCRIPT}
        strategy="afterInteractive"
        onLoad={() => setScriptReady(true)}
      />

      <div className="flex items-center gap-3">
        <AddiMark />
        <div>
          <p className="text-sm font-semibold text-dark">Compra hoy, paga después</p>
          <p className="mt-0.5 text-xs leading-5 text-dark-3">
            Consulta tus opciones de financiación con Addi.
          </p>
        </div>
      </div>

      <div className="mt-4 min-h-[38px] rounded-lg bg-white px-3 py-2 shadow-1">
        {scriptReady ? (
          widget
        ) : (
          <p className="text-xs leading-6 text-dark-3">Cargando opciones de pago…</p>
        )}
      </div>

      <p className="mt-2 text-[11px] leading-4 text-dark-3">
        Sujeto a aprobación y condiciones de Addi.
      </p>
    </section>
  );
}
