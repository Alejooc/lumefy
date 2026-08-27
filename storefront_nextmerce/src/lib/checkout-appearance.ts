import type { CSSProperties } from "react";

export type CheckoutAppearance = {
  background_color: string;
  card_background_color: string;
  accent_color: string;
  accent_text_color: string;
  field_background_color: string;
  border_color: string;
  radius: number;
  layout: "split" | "stacked";
  show_logo: boolean;
  show_brand_name: boolean;
};

export const DEFAULT_CHECKOUT_APPEARANCE: CheckoutAppearance = {
  background_color: "#f4f6fb",
  card_background_color: "#ffffff",
  accent_color: "#3c50e0",
  accent_text_color: "#ffffff",
  field_background_color: "#f8fafc",
  border_color: "#d9e1ec",
  radius: 12,
  layout: "split",
  show_logo: true,
  show_brand_name: true,
};

const HEX_COLOR = /^#[0-9a-f]{6}$/i;

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function safeHex(value: unknown, fallback: string): string {
  const candidate = typeof value === "string" ? value.trim() : "";
  return HEX_COLOR.test(candidate) ? candidate : fallback;
}

function safeRadius(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? Math.max(0, Math.min(24, Math.round(parsed)))
    : DEFAULT_CHECKOUT_APPEARANCE.radius;
}

export function normalizeCheckoutAppearance(value: unknown): CheckoutAppearance {
  const appearance = objectValue(value);
  return {
    background_color: safeHex(appearance.background_color, DEFAULT_CHECKOUT_APPEARANCE.background_color),
    card_background_color: safeHex(appearance.card_background_color, DEFAULT_CHECKOUT_APPEARANCE.card_background_color),
    accent_color: safeHex(appearance.accent_color, DEFAULT_CHECKOUT_APPEARANCE.accent_color),
    accent_text_color: safeHex(appearance.accent_text_color, DEFAULT_CHECKOUT_APPEARANCE.accent_text_color),
    field_background_color: safeHex(appearance.field_background_color, DEFAULT_CHECKOUT_APPEARANCE.field_background_color),
    border_color: safeHex(appearance.border_color, DEFAULT_CHECKOUT_APPEARANCE.border_color),
    radius: safeRadius(appearance.radius),
    layout: appearance.layout === "stacked" ? "stacked" : "split",
    show_logo: appearance.show_logo !== false,
    show_brand_name: appearance.show_brand_name !== false,
  };
}

export function checkoutAppearanceVariables(appearance: CheckoutAppearance): CSSProperties {
  return {
    "--checkout-page-background": appearance.background_color,
    "--checkout-card-background": appearance.card_background_color,
    "--checkout-accent": appearance.accent_color,
    "--checkout-accent-text": appearance.accent_text_color,
    "--checkout-field-background": appearance.field_background_color,
    "--checkout-border": appearance.border_color,
    "--checkout-radius": `${appearance.radius}px`,
  } as CSSProperties;
}
