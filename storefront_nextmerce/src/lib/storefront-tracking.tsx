"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { getPublicTrackingIntegrations, sendPublicTrackingEvent } from "@/lib/storefront-api";
import type { PublicTrackingEventRequest, PublicTrackingIntegration } from "@/types/storefront";

export type TrackingItem = {
  item_id: string;
  item_name: string;
  price: number;
  quantity: number;
  item_variant?: string;
  item_category?: string;
  item_brand?: string;
};

export type StorefrontTrackingEvent = {
  name:
    | "page_view"
    | "view_item"
    | "search"
    | "add_to_cart"
    | "remove_from_cart"
    | "view_cart"
    | "begin_checkout"
    | "add_shipping_info"
    | "add_payment_info"
    | "purchase";
  event_id?: string;
  currency?: string;
  value?: number;
  transaction_id?: string;
  search_term?: string;
  client_id?: string;
  page_location?: string;
  items?: TrackingItem[];
};

export type TrackingConsent = {
  analytics: boolean;
  marketing: boolean;
};

type QueueFunction = ((...args: unknown[]) => void) & Record<string, unknown>;

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
    fbq?: QueueFunction;
    _fbq?: QueueFunction;
    ttq?: unknown;
    TiktokAnalyticsObject?: string;
  }
}

const CONSENT_STORAGE_KEY = "lumefy-tracking-consent-v1";
const CLIENT_ID_STORAGE_KEY = "lumefy-tracking-client-id-v1";
const PURCHASE_STORAGE_KEY = "lumefy-pending-purchase-v1";
const CONFIRMED_PAYMENT_STATUSES = new Set([
  "approved",
  "approved_partial",
  "approved_stock_unavailable",
  "paid",
  "succeeded",
  "success",
]);
const MAX_PENDING_EVENTS = 50;
const initializedIntegrations = new Set<string>();
let activeIntegrations: PublicTrackingIntegration[] = [];
let activeConsent: TrackingConsent | null = null;
let activeCurrency = "USD";
let activeStorefrontId: string | null = null;
let configurationLoaded = false;
let pendingEvents: StorefrontTrackingEvent[] = [];
let pendingConfirmedPurchase: StorefrontTrackingEvent | null = null;

function uniqueEventId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}:${crypto.randomUUID()}`;
  }
  return `${prefix}:${Date.now()}:${Math.random().toString(36).slice(2, 10)}`;
}

function scopedConsentKey(): string {
  if (typeof window === "undefined") return CONSENT_STORAGE_KEY;
  return `${CONSENT_STORAGE_KEY}:${window.location.host.toLowerCase()}`;
}

function readConsent(): TrackingConsent | null {
  if (typeof window === "undefined") return null;
  try {
    const value = JSON.parse(window.localStorage.getItem(scopedConsentKey()) || "null") as unknown;
    if (!value || typeof value !== "object") return null;
    const record = value as Record<string, unknown>;
    return {
      analytics: record.analytics === true,
      marketing: record.marketing === true,
    };
  } catch {
    return null;
  }
}

export function getStorefrontTrackingConsent(): TrackingConsent {
  return readConsent() || { analytics: false, marketing: false };
}

function getTrackingClientId(): string {
  if (typeof window === "undefined") return "server";
  const key = `${CLIENT_ID_STORAGE_KEY}:${window.location.host.toLowerCase()}`;
  try {
    const stored = window.localStorage.getItem(key);
    if (stored) return stored;
    const value = uniqueEventId("client");
    window.localStorage.setItem(key, value);
    return value;
  } catch {
    return uniqueEventId("client");
  }
}

function appendScript(id: string, src: string): void {
  if (document.getElementById(id)) return;
  const script = document.createElement("script");
  script.id = id;
  script.async = true;
  script.src = src;
  document.head.appendChild(script);
}

function initializeGoogleAnalytics(trackingId: string): void {
  const key = `google:${trackingId}`;
  if (initializedIntegrations.has(key)) return;
  initializedIntegrations.add(key);
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || ((...args: unknown[]) => window.dataLayer?.push(args));
  window.gtag("js", new Date());
  window.gtag("config", trackingId, { send_page_view: false });
  appendScript(`lumefy-ga-${trackingId}`, `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(trackingId)}`);
}

function initializeMetaPixel(pixelId: string): void {
  const key = `meta:${pixelId}`;
  if (initializedIntegrations.has(key)) return;
  initializedIntegrations.add(key);

  if (!window.fbq) {
    const fbq = function (...args: unknown[]) {
      const current = window.fbq as QueueFunction & { callMethod?: (...values: unknown[]) => void; queue?: unknown[][] };
      if (current.callMethod) current.callMethod(...args);
      else (current.queue ||= []).push(args);
    } as QueueFunction & { loaded?: boolean; version?: string; queue?: unknown[][] };
    fbq.loaded = true;
    fbq.version = "2.0";
    fbq.queue = [];
    fbq.push = fbq;
    window.fbq = fbq;
    window._fbq = fbq;
  }
  appendScript("lumefy-meta-pixel", "https://connect.facebook.net/en_US/fbevents.js");
  window.fbq?.("init", pixelId);
}

function initializeTikTokPixel(pixelId: string): void {
  const key = `tiktok:${pixelId}`;
  if (initializedIntegrations.has(key)) return;
  initializedIntegrations.add(key);

  const ttq = (window.ttq || []) as unknown[] & Record<string, unknown>;
  window.TiktokAnalyticsObject = "ttq";
  window.ttq = ttq;
  const methods = [
    "page", "track", "identify", "instances", "debug", "on", "off", "once", "ready", "alias", "group", "enableCookie", "disableCookie",
  ];
  const setAndDefer = (target: unknown[] & Record<string, unknown>, method: string) => {
    target[method] = (...args: unknown[]) => target.push([method, ...args]);
  };
  methods.forEach((method) => setAndDefer(ttq, method));
  ttq._i = ttq._i || {};
  ttq._t = ttq._t || {};
  ttq._o = ttq._o || {};
  (ttq._i as Record<string, unknown>)[pixelId] = [];
  (ttq._t as Record<string, unknown>)[pixelId] = Date.now();
  (ttq._o as Record<string, unknown>)[pixelId] = {};
  appendScript(
    `lumefy-tiktok-${pixelId}`,
    `https://analytics.tiktok.com/i18n/pixel/events.js?sdkid=${encodeURIComponent(pixelId)}&lib=ttq`,
  );
}

function ecommercePayload(event: StorefrontTrackingEvent): Record<string, unknown> {
  return {
    ...(event.currency ? { currency: event.currency } : {}),
    ...(typeof event.value === "number" ? { value: event.value } : {}),
    ...(event.transaction_id ? { transaction_id: event.transaction_id } : {}),
    ...(event.search_term ? { search_term: event.search_term } : {}),
    ...(event.items?.length ? { items: event.items } : {}),
  };
}

function sendGoogleEvent(integration: PublicTrackingIntegration, event: StorefrontTrackingEvent): void {
  if (!window.gtag) return;
  if (!integration.track_ecommerce && event.name !== "page_view") return;
  window.gtag("event", event.name, {
    ...ecommercePayload(event),
    event_id: event.event_id,
    page_location: window.location.href,
  });
}

function sendMetaEvent(integration: PublicTrackingIntegration, event: StorefrontTrackingEvent): void {
  if (!window.fbq) return;
  const eventMap: Partial<Record<StorefrontTrackingEvent["name"], string>> = {
    page_view: "PageView",
    view_item: "ViewContent",
    search: "Search",
    add_to_cart: "AddToCart",
    remove_from_cart: "RemoveFromCart",
    view_cart: "ViewCart",
    begin_checkout: "InitiateCheckout",
    add_shipping_info: "AddShippingInfo",
    add_payment_info: "AddPaymentInfo",
    purchase: "Purchase",
  };
  const providerEvent = eventMap[event.name];
  if (!providerEvent || (!integration.track_ecommerce && event.name !== "page_view")) return;
  const contents = (event.items || []).map((item) => ({
    id: item.item_id,
    quantity: item.quantity,
    item_price: item.price,
  }));
  window.fbq("track", providerEvent, {
    content_ids: contents.map((item) => item.id),
    contents,
    content_type: "product",
    ...(event.search_term ? { search_string: event.search_term } : {}),
    ...(event.currency ? { currency: event.currency } : {}),
    ...(typeof event.value === "number" ? { value: event.value } : {}),
  }, { eventID: event.event_id });
}

function sendTikTokEvent(integration: PublicTrackingIntegration, event: StorefrontTrackingEvent): void {
  const ttq = window.ttq as { page?: () => void; track?: (...args: unknown[]) => void } | undefined;
  if (!ttq) return;
  if (event.name === "page_view") {
    ttq.page?.();
    return;
  }
  if (!integration.track_ecommerce) return;
  const eventMap: Partial<Record<StorefrontTrackingEvent["name"], string>> = {
    view_item: "ViewContent",
    search: "Search",
    add_to_cart: "AddToCart",
    remove_from_cart: "RemoveFromCart",
    view_cart: "ViewCart",
    begin_checkout: "InitiateCheckout",
    add_shipping_info: "AddShippingInfo",
    add_payment_info: "AddPaymentInfo",
    purchase: "Purchase",
  };
  const providerEvent = eventMap[event.name];
  if (!providerEvent) return;
  const items = event.items || [];
  ttq.track?.(providerEvent, {
    contents: items.map((item) => ({
      content_id: item.item_id,
      content_name: item.item_name,
      content_type: "product",
      quantity: item.quantity,
      price: item.price,
    })),
    ...(event.search_term ? { query: event.search_term } : {}),
    ...(event.currency ? { currency: event.currency } : {}),
    ...(typeof event.value === "number" ? { value: event.value } : {}),
  }, { event_id: event.event_id });
}

function integrationAllowed(integration: PublicTrackingIntegration): boolean {
  if (!activeConsent) return false;
  return integration.consent_category === "analytics"
    ? activeConsent.analytics
    : activeConsent.marketing;
}

function shouldSendServerSide(event: StorefrontTrackingEvent): boolean {
  if (!activeStorefrontId || event.name === "purchase") return false;
  return activeIntegrations.some((integration) => (
    integration.server_side_enabled
    && integrationAllowed(integration)
    && (event.name === "page_view" || integration.track_ecommerce)
  ));
}

function dispatchTrackingEvent(event: StorefrontTrackingEvent): void {
  for (const integration of activeIntegrations) {
    if (!integrationAllowed(integration)) continue;
    if (!integration.enabled) continue;
    if (integration.provider === "google_analytics") sendGoogleEvent(integration, event);
    if (integration.provider === "meta") sendMetaEvent(integration, event);
    if (integration.provider === "tiktok") sendTikTokEvent(integration, event);
  }
  if (shouldSendServerSide(event)) {
    if (event.name === "purchase") return;
    const serverEvent: PublicTrackingEventRequest = {
      name: event.name,
      event_id: event.event_id || uniqueEventId(event.name),
      client_id: event.client_id,
      currency: event.currency,
      value: event.value,
      transaction_id: event.transaction_id,
      search_term: event.search_term,
      page_location: event.page_location,
      items: event.items,
      consent: activeConsent || { analytics: false, marketing: false },
    };
    void sendPublicTrackingEvent(activeStorefrontId as string, serverEvent).catch(() => {
      // Browser tracking remains available if the public endpoint is unavailable.
    });
  }
}

function configureTracking(
  storefrontId: string,
  integrations: PublicTrackingIntegration[],
  consent: TrackingConsent | null,
  currency: string,
): void {
  activeStorefrontId = storefrontId;
  activeIntegrations = integrations;
  activeConsent = consent;
  activeCurrency = currency || "USD";
  configurationLoaded = true;
  for (const integration of integrations) {
    if (!integrationAllowed(integration)) continue;
    if (!integration.enabled) continue;
    if (integration.provider === "google_analytics") initializeGoogleAnalytics(integration.tracking_id);
    if (integration.provider === "meta") initializeMetaPixel(integration.tracking_id);
    if (integration.provider === "tiktok") initializeTikTokPixel(integration.tracking_id);
  }
  const queued = pendingEvents;
  pendingEvents = [];
  queued.forEach(dispatchTrackingEvent);
  if (pendingConfirmedPurchase) {
    const confirmedPurchase = pendingConfirmedPurchase;
    pendingConfirmedPurchase = null;
    dispatchTrackingEvent(confirmedPurchase);
  }
}

export function trackStorefrontEvent(event: StorefrontTrackingEvent): void {
  if (typeof window === "undefined") return;
  if (!activeConsent) activeConsent = readConsent();
  if (!activeConsent) return;
  const normalizedEvent = {
    ...event,
    event_id: event.event_id || uniqueEventId(event.name),
    currency: event.currency || activeCurrency,
    client_id: event.client_id || getTrackingClientId(),
    page_location: event.page_location || window.location.href,
  };
  if (!configurationLoaded) {
    pendingEvents = [...pendingEvents.slice(-(MAX_PENDING_EVENTS - 1)), normalizedEvent];
    return;
  }
  dispatchTrackingEvent(normalizedEvent);
}

export function rememberPendingStorefrontPurchase(event: StorefrontTrackingEvent): void {
  if (typeof window === "undefined" || !event.transaction_id) return;
  window.sessionStorage.setItem(PURCHASE_STORAGE_KEY, JSON.stringify(event));
}

export function trackPendingStorefrontPurchase(
  transactionId: string | undefined,
  paymentStatus?: string,
  fallback?: Pick<StorefrontTrackingEvent, "currency" | "value">,
): void {
  if (typeof window === "undefined" || !transactionId) return;
  const normalizedStatus = (paymentStatus || "pending").toLowerCase();
  if (!CONFIRMED_PAYMENT_STATUSES.has(normalizedStatus)) return;

  const sentKey = `${PURCHASE_STORAGE_KEY}:sent:${transactionId}`;
  if (window.sessionStorage.getItem(sentKey)) return;

  let pendingEvent: StorefrontTrackingEvent | null = null;
  try {
    const stored = JSON.parse(window.sessionStorage.getItem(PURCHASE_STORAGE_KEY) || "null") as unknown;
    if (stored && typeof stored === "object" && (stored as StorefrontTrackingEvent).transaction_id === transactionId) {
      pendingEvent = stored as StorefrontTrackingEvent;
    }
  } catch {
    pendingEvent = null;
  }

  const event: StorefrontTrackingEvent = pendingEvent || {
    name: "purchase",
    event_id: `purchase:${transactionId}`,
    transaction_id: transactionId,
    currency: fallback?.currency,
    value: fallback?.value,
  };
  window.sessionStorage.setItem(sentKey, "1");
  window.sessionStorage.removeItem(PURCHASE_STORAGE_KEY);
  if (!configurationLoaded) {
    pendingConfirmedPurchase = event;
    return;
  }
  trackStorefrontEvent(event);
}

export function trackingItem(input: {
  id?: string | number;
  publishedProductId?: string;
  title: string;
  discountedPrice: number;
  quantity?: number;
  variantName?: string;
  categoryName?: string;
  brandName?: string;
}): TrackingItem {
  return {
    item_id: input.publishedProductId || String(input.id || "product"),
    item_name: input.title,
    price: Number(input.discountedPrice || 0),
    quantity: Math.max(1, Number(input.quantity || 1)),
    ...(input.variantName ? { item_variant: input.variantName } : {}),
    ...(input.categoryName ? { item_category: input.categoryName } : {}),
    ...(input.brandName ? { item_brand: input.brandName } : {}),
  };
}

function CookiePreferences({
  consent,
  onSave,
  onClose,
}: {
  consent: TrackingConsent;
  onSave: (consent: TrackingConsent) => void;
  onClose?: () => void;
}) {
  const [draft, setDraft] = useState(consent);
  return (
    <div className="fixed inset-x-4 bottom-4 z-[10000] mx-auto max-w-[720px] overflow-hidden rounded-[22px] border border-white/10 bg-[#17233f] text-white shadow-[0_24px_80px_rgba(15,23,42,.36)] sm:bottom-6">
      <div className="grid gap-5 p-5 sm:grid-cols-[1fr_auto] sm:p-6">
        <div>
          <span className="mb-2 inline-flex rounded-full bg-white/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#f4c7a8]">Privacidad</span>
          <h2 className="text-lg font-semibold">Tú eliges cómo medimos la experiencia</h2>
          <p className="mt-2 max-w-[520px] text-sm leading-6 text-white/70">Usamos cookies de analítica y marketing únicamente con tu permiso. Las necesarias mantienen funcionando la tienda y el checkout.</p>
        </div>
        {onClose ? (
          <button type="button" onClick={onClose} className="absolute right-4 top-4 text-xl text-white/50 hover:text-white" aria-label="Cerrar preferencias">×</button>
        ) : null}
        <div className="flex min-w-[190px] flex-col justify-center gap-3 text-sm">
          <label className="flex cursor-pointer items-center justify-between gap-5 rounded-xl bg-white/[0.08] px-4 py-3">
            <span>Analítica</span>
            <input type="checkbox" checked={draft.analytics} onChange={(event) => setDraft((current) => ({ ...current, analytics: event.target.checked }))} className="h-4 w-4 accent-[#f4c7a8]" />
          </label>
          <label className="flex cursor-pointer items-center justify-between gap-5 rounded-xl bg-white/[0.08] px-4 py-3">
            <span>Marketing</span>
            <input type="checkbox" checked={draft.marketing} onChange={(event) => setDraft((current) => ({ ...current, marketing: event.target.checked }))} className="h-4 w-4 accent-[#f4c7a8]" />
          </label>
        </div>
      </div>
      <div className="flex flex-wrap justify-end gap-2 border-t border-white/10 bg-black/10 px-5 py-4 sm:px-6">
        <button type="button" onClick={() => onSave({ analytics: false, marketing: false })} className="rounded-full border border-white/20 px-4 py-2 text-xs font-semibold transition hover:bg-white/10">Solo necesarias</button>
        <button type="button" onClick={() => onSave(draft)} className="rounded-full bg-white px-4 py-2 text-xs font-semibold text-[#17233f] transition hover:bg-[#f4c7a8]">Guardar preferencias</button>
        <button type="button" onClick={() => onSave({ analytics: true, marketing: true })} className="rounded-full bg-[#b65332] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#cf6744]">Aceptar todas</button>
      </div>
    </div>
  );
}

export function StorefrontTrackingProvider({
  storefrontId,
  currency,
  children,
}: {
  storefrontId: string;
  currency: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const [integrations, setIntegrations] = useState<PublicTrackingIntegration[]>([]);
  const [configurationResolved, setConfigurationResolved] = useState(false);
  const [consent, setConsent] = useState<TrackingConsent | null>(() => readConsent());
  const [preferencesOpen, setPreferencesOpen] = useState(() => readConsent() === null);

  useEffect(() => {
    let active = true;
    getPublicTrackingIntegrations(storefrontId)
      .then((items) => {
        if (active) {
          setIntegrations(items);
          setConfigurationResolved(true);
        }
      })
      .catch(() => {
        if (active) {
          setIntegrations([]);
          setConfigurationResolved(true);
        }
      });
    return () => {
      active = false;
    };
  }, [storefrontId]);

  useEffect(() => {
    if (!configurationResolved) return;
    configureTracking(storefrontId, integrations, consent, currency);
    if (consent && integrations.some(integrationAllowed)) {
      trackStorefrontEvent({ name: "page_view" });
      const searchTerm = new URLSearchParams(window.location.search).get("q")?.trim();
      if (searchTerm) trackStorefrontEvent({ name: "search", search_term: searchTerm });
    }
  }, [configurationResolved, consent, currency, integrations, pathname]);

  const saveConsent = (nextConsent: TrackingConsent) => {
    const shouldReload = Boolean(consent?.analytics && !nextConsent.analytics)
      || Boolean(consent?.marketing && !nextConsent.marketing);
    window.localStorage.setItem(scopedConsentKey(), JSON.stringify(nextConsent));
    setConsent(nextConsent);
    setPreferencesOpen(false);
    if (shouldReload) window.location.reload();
  };

  return (
    <>
      {children}
      {configurationResolved && integrations.length > 0 && preferencesOpen ? (
        <CookiePreferences
          consent={consent || { analytics: false, marketing: false }}
          onSave={saveConsent}
          onClose={consent ? () => setPreferencesOpen(false) : undefined}
        />
      ) : configurationResolved && integrations.length > 0 ? (
        <button
          type="button"
          onClick={() => setPreferencesOpen(true)}
          className="fixed bottom-3 left-3 z-[9998] rounded-full border border-gray-3 bg-white/95 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#17233f] shadow-sm backdrop-blur transition hover:border-[#17233f] sm:bottom-4 sm:left-4"
        >
          Privacidad
        </button>
      ) : null}
    </>
  );
}
