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
  PublicStoreNavigationItem,
  PublicStorefront,
} from "@/types/storefront";

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
  const isCacheableGet = method === "GET" && !hasAuthorization;

  const response = await fetch(makeUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: init?.cache ?? (isCacheableGet ? "force-cache" : "no-store"),
    next:
      "next" in (init || {})
        ? (init as RequestInit & { next?: { revalidate?: number } }).next
        : isCacheableGet
          ? { revalidate: 60 }
          : undefined,
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
  return request<PublicStorefront>(`/storefront/public/by-subdomain/${encodeURIComponent(subdomain)}`);
}

export async function getPublicStorefrontByDomain(domain: string): Promise<PublicStorefront> {
  return request<PublicStorefront>(`/storefront/public/by-domain/${encodeURIComponent(domain)}`);
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
  return request<PublicCollection[]>(`/storefront/public/${storefrontId}/collections`);
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
  return request<PublicCatalogResponse>(`/storefront/public/${storefrontId}/products${suffix}`);
}

export async function getPublicCollectionBySlug(storefrontId: string, slug: string): Promise<PublicCollection> {
  return request<PublicCollection>(`/storefront/public/${storefrontId}/collections/${encodeURIComponent(slug)}`);
}

export async function getPublicProductBySlug(storefrontId: string, slug: string): Promise<PublicProduct> {
  return request<PublicProduct>(`/storefront/public/${storefrontId}/products/${encodeURIComponent(slug)}`);
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
): Promise<CheckoutCreateOrderResponse> {
  return request<CheckoutCreateOrderResponse>(`/storefront/public/${storefrontId}/checkout/orders`, {
    method: "POST",
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

export async function resolveStorefront(): Promise<PublicStorefront> {
  const storefrontId = process.env.NEXT_PUBLIC_STOREFRONT_ID?.trim();
  const storefrontSubdomain = process.env.NEXT_PUBLIC_STOREFRONT_SUBDOMAIN?.trim();

  if (storefrontSubdomain) {
    return getPublicStorefrontBySubdomain(storefrontSubdomain);
  }

  if (storefrontId) {
    return getPublicStorefront(storefrontId);
  }

  if (typeof window !== "undefined" && window.location.hostname) {
    return getPublicStorefrontByDomain(window.location.hostname);
  }

  // Keep one storefront runtime for every tenant: the incoming host selects its data.
  const { headers } = await import("next/headers");
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") || requestHeaders.get("host");
  if (host) {
    return getPublicStorefrontByDomain(host);
  }

  throw new Error("Missing storefront configuration. Define a storefront ID/subdomain or access through a mapped domain.");
}
