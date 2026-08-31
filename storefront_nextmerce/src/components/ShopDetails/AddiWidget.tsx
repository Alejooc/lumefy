"use client";

import React from "react";
import Script from "next/script";
import { ADDI_MINIMUM_AMOUNT_COP } from "@/lib/addi";

const ADDI_WIDGET_SCRIPT = "https://s3.amazonaws.com/widgets.addi.com/bundle.min.js";

export type AddiWidgetConfig = {
  allySlug: string;
  isSandbox?: boolean;
};

export default function AddiWidget({ price, config }: { price: number; config: AddiWidgetConfig }) {
  const normalizedPrice = Math.max(0, Math.round(Number(price) || 0));
  const allySlug = config.allySlug.trim();

  if (!allySlug || normalizedPrice < ADDI_MINIMUM_AMOUNT_COP) return null;

  const widget = React.createElement("addi-widget", {
    key: `${allySlug}-${normalizedPrice}`,
    price: String(normalizedPrice),
    "ally-slug": allySlug,
  });

  return (
    <div className="mt-5">
      <Script
        id="addi-widget-script"
        src={ADDI_WIDGET_SCRIPT}
        strategy="afterInteractive"
      />
      {widget}
    </div>
  );
}
