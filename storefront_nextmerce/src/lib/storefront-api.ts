import {
  CheckoutCreateOrderRequest,
  CheckoutCreateOrderResponse,
  CheckoutPreviewRequest,
  CheckoutPreviewResponse,
  PaymentIntentRequest,
  PaymentIntentResponse,
  PaymentStatusResponse,
  PublicStorefrontAccountOrder,
  PublicStorefrontAccountUser,
  PublicStorefrontAuthResponse,
  PublicCollection,
  PublicCatalogResponse,
  PublicProduct,
  PublicStorePaymentGateway,
  PublicShippingConfig,
  PublicStoreNavigationItem,
  PublicStorefront,
} from "@/types/storefront";
import { cache } from "react";
import { resolveStorefrontHost } from "./storefront-host";

const PREVIEW_TOKEN_COOKIE = "lumefy_preview_token";

export class StorefrontApiError extends Error {
  status: number;
  payload?: unknown;

  constructor(message: string, status: number, payload?: unknown) {
    super(message);
    this.name = "StorefrontApiError";
    this.status = status;
    this.payload = payload;
  }
}

function apiBaseUrl(): string {
  const value =
    typeof window === "undefined"
      ? process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL
      : process.env.NEXT_PUBLIC_API_URL;
  if (!value) {
    throw new Error("Missing storefront API URL configuration");
  }
  if (typeof window === "undefined" && value.startsWith("/")) {
    throw new Error("INTERNAL_API_URL must be absolute when rendering the storefront server-side");
  }
  return value.replace(/\/$/, "");
}

function makeUrl(path: string): string {
  return `${apiBaseUrl()}${path}`;
}

async function currentPreviewToken(): Promise<string | null> {
  if (typeof window !== "undefined") {
    const fromUrl = new URL(window.location.href).searchParams.get("preview_token");
    if (fromUrl) return fromUrl;
    const cookie = document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(`${PREVIEW_TOKEN_COOKIE}=`));
    return cookie ? decodeURIComponent(cookie.slice(PREVIEW_TOKEN_COOKIE.length + 1)) : null;
  }

  const { cookies, headers } = await import("next/headers");
  const requestHeaders = await headers();
  return (
    requestHeaders.get("x-lumefy-preview-token") ||
    (await cookies()).get(PREVIEW_TOKEN_COOKIE)?.value ||
    null
  );
}

function withPreviewToken(path: string, previewToken: string): string {
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}preview_token=${encodeURIComponent(previewToken)}`;
}

async function parseJsonSafe(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method || "GET").toUpperCase();
  const hasAuthorization =
    init?.headers instanceof Headers
      ? init.headers.has("Authorization")
      : Boolean(
          init?.headers &&
            "Authorization" in (init.headers as Record<string, string | undefined>),
        );
  const previewToken = method === "GET" ? await currentPreviewToken() : null;
  const requestPath =
    previewToken && path.startsWith("/storefront/public/")
      ? withPreviewToken(path, previewToken)
      : path;
  const isCacheableGet = method === "GET" && !hasAuthorization && !previewToken;
  const cacheMode = previewToken ? "no-store" : (init?.cache ?? (isCacheableGet ? "force-cache" : "no-store"));
  const nextOptions = previewToken
    ? undefined
    : "next" in (init || {})
      ? (init as RequestInit & { next?: { revalidate?: number } }).next
      : isCacheableGet && cacheMode !== "no-store"
        ? { revalidate: 60 }
        : undefined;

  const response = await fetch(makeUrl(requestPath), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: cacheMode,
    next: nextOptions,
  });

  if (!response.ok) {
    const payload = await parseJsonSafe(response);
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String((payload as { detail?: unknown }).detail)
        : `Request failed with status ${response.status}`;
    throw new StorefrontApiError(detail, response.status, payload);
  }

  return (await response.json()) as T;
}

export async function getPublicStorefrontBySubdomain(subdomain: string): Promise<PublicStorefront> {
  return request<PublicStorefront>(`/storefront/public/by-subdomain/${encodeURIComponent(subdomain)}`, {
    // Branding and metadata can change from the admin panel. Do not let a
    // cached response keep serving an old logo or favicon after publishing.
    cache: "no-store",
  });
}

export async function getPublicStorefrontByDomain(domain: string): Promise<PublicStorefront> {
  return request<PublicStorefront>(`/storefront/public/by-domain/${encodeURIComponent(domain)}`, {
    cache: "no-store",
  });
}

export async function getPublicStorefront(storefrontId: string): Promise<PublicStorefront> {
  return request<PublicStorefront>(`/storefront/public/${storefrontId}`);
}

export async function getPublicNavigation(
  storefrontId: string,
): Promise<PublicStoreNavigationItem[]> {
  return request<PublicStoreNavigationItem[]>(
    `/storefront/public/${storefrontId}/navigation`,
    { cache: "no-store" },
  );
}

export async function getPublicPaymentGateways(
  storefrontId: string,
): Promise<PublicStorePaymentGateway[]> {
  return request<PublicStorePaymentGateway[]>(
    `/storefront/public/${storefrontId}/payment-gateways`,
    { cache: "no-store" },
  );
}

export async function getPublicCollections(storefrontId: string): Promise<PublicCollection[]> {
  return request<PublicCollection[]>(`/storefront/public/${storefrontId}/collections`, {
    // Collections are catalog navigation metadata, not inventory. A short
    // cache prevents every page change from refetching the same list.
    cache: "force-cache",
  });
}

export async function getPublicShippingConfig(
  storefrontId: string,
): Promise<PublicShippingConfig> {
  return request<PublicShippingConfig>(
    `/storefront/public/${storefrontId}/shipping/config`,
    { cache: "no-store" },
  );
}

export async function getPublicProducts(
  storefrontId: string,
  params?: Record<string, string | number | undefined>,
): Promise<PublicCatalogResponse> {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    search.set(key, String(value));
  }
  const suffix = search.toString() ? `?${search.toString()}` : "";
  // A short cache prevents every navigation/infinite-scroll request from
  // recalculating the same catalog. Checkout still validates stock in the
  // backend, so a few seconds of catalog cache cannot oversell inventory.
  return request<PublicCatalogResponse>(`/storefront/public/${storefrontId}/products${suffix}`, {
    cache: "force-cache",
    next: { revalidate: 15 },
  });
}

export async function getPublicCollectionBySlug(storefrontId: string, slug: string): Promise<PublicCollection> {
  return request<PublicCollection>(
    `/storefront/public/${storefrontId}/collections/${encodeURIComponent(slug)}`,
    { cache: "no-store" },
  );
}

export async function getPublicProductBySlug(storefrontId: string, slug: string): Promise<PublicProduct> {
  return request<PublicProduct>(
    `/storefront/public/${storefrontId}/products/${encodeURIComponent(slug)}`,
    { cache: "no-store" },
  );
}

export async function checkoutPreview(
  storefrontId: string,
  payload: CheckoutPreviewRequest,
): Promise<CheckoutPreviewResponse> {
  return request<CheckoutPreviewResponse>(`/storefront/public/${storefrontId}/checkout/preview`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createCheckoutOrder(
  storefrontId: string,
  payload: CheckoutCreateOrderRequest,
  token?: string,
): Promise<CheckoutCreateOrderResponse> {
  return request<CheckoutCreateOrderResponse>(`/storefront/public/${storefrontId}/checkout/orders`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(payload),
  });
}

export async function createPaymentIntent(
  storefrontId: string,
  payload: PaymentIntentRequest,
): Promise<PaymentIntentResponse> {
  return request<PaymentIntentResponse>(`/storefront/public/${storefrontId}/checkout/payment-intent`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getPaymentStatus(
  storefrontId: string,
  params: { provider: string; transaction_id: string },
): Promise<PaymentStatusResponse> {
  const search = new URLSearchParams({
    provider: params.provider,
    transaction_id: params.transaction_id,
  });
  return request<PaymentStatusResponse>(
    `/storefront/public/${storefrontId}/checkout/payment-status?${search.toString()}`,
    { cache: "no-store" },
  );
}

export async function registerStorefrontAccount(
  storefrontId: string,
  payload: { full_name: string; email: string; password: string },
): Promise<PublicStorefrontAuthResponse> {
  return request<PublicStorefrontAuthResponse>(`/storefront/public/${storefrontId}/auth/register`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function loginStorefrontAccount(
  storefrontId: string,
  payload: { email: string; password: string },
): Promise<PublicStorefrontAuthResponse> {
  return request<PublicStorefrontAuthResponse>(`/storefront/public/${storefrontId}/auth/login`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getStorefrontAccountMe(
  storefrontId: string,
  token: string,
): Promise<PublicStorefrontAccountUser> {
  return request<PublicStorefrontAccountUser>(`/storefront/public/${storefrontId}/account/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateStorefrontAccountProfile(
  storefrontId: string,
  token: string,
  payload: { full_name: string },
): Promise<PublicStorefrontAccountUser> {
  return request<PublicStorefrontAccountUser>(`/storefront/public/${storefrontId}/account/profile`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function changeStorefrontAccountPassword(
  storefrontId: string,
  token: string,
  payload: { current_password: string; new_password: string },
): Promise<{ msg: string }> {
  return request<{ msg: string }>(`/storefront/public/${storefrontId}/account/password`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getStorefrontAccountOrders(
  storefrontId: string,
  token: string,
): Promise<PublicStorefrontAccountOrder[]> {
  return request<PublicStorefrontAccountOrder[]>(`/storefront/public/${storefrontId}/account/orders`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function requestStorefrontPasswordRecovery(
  storefrontId: string,
  payload: { email: string },
): Promise<{ msg: string }> {
  return request<{ msg: string }>(`/storefront/public/${storefrontId}/auth/password-recovery`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function resetStorefrontPassword(
  storefrontId: string,
  payload: { token: string; new_password: string },
): Promise<{ msg: string }> {
  return request<{ msg: string }>(`/storefront/public/${storefrontId}/auth/reset-password`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function sendStorefrontContactMessage(
  storefrontId: string,
  payload: {
    first_name: string;
    last_name: string;
    email: string;
    subject?: string;
    phone?: string;
    message: string;
  },
): Promise<{ msg: string }> {
  return request<{ msg: string }>(`/storefront/public/${storefrontId}/contact`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function subscribeStorefrontNewsletter(
  storefrontId: string,
  email: string,
): Promise<{ msg: string }> {
  return request<{ msg: string }>(`/storefront/public/${storefrontId}/newsletter`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export const resolveStorefront = cache(async (): Promise<PublicStorefront> => {
  const baseDomain = process.env.NEXT_PUBLIC_PLATFORM_STOREFRONT_DOMAIN;
  let host = "";

  if (typeof window !== "undefined") {
    host = window.location.host;
  } else {
    // Reading request headers marks the route as request-specific, preventing
    // one tenant's rendered storefront from being reused for another host.
    const { headers } = await import("next/headers");
    const requestHeaders = await headers();
    host = requestHeaders.get("x-forwarded-host") || requestHeaders.get("host") || "";
  }

  const target = resolveStorefrontHost(host, baseDomain);
  if (!target) {
    throw new Error("Missing storefront host. Access the store through a mapped subdomain or custom domain.");
  }

  return target.type === "subdomain"
    ? getPublicStorefrontBySubdomain(target.value)
    : getPublicStorefrontByDomain(target.value);
});
