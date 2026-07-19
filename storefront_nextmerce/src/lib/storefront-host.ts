export type StorefrontHostTarget =
  | { type: "subdomain"; value: string }
  | { type: "domain"; value: string };

/**
 * Normalizes a request host before using it as a storefront identity. Hosts
 * may include a port locally or be supplied through a forwarded-host header.
 */
export function normalizeStorefrontHost(value: string | null | undefined): string {
  const rawHost = value?.split(",")[0]?.trim().toLowerCase() || "";
  if (!rawHost) {
    return "";
  }

  const host = rawHost.replace(/^https?:\/\//, "").split("/")[0];
  return host.replace(/:\d+$/, "").replace(/\.$/, "");
}

/**
 * Maps tenant subdomains to the shared storefront runtime. Any host outside
 * the Lumefy base domain is treated as a verified custom domain.
 */
export function resolveStorefrontHost(
  host: string | null | undefined,
  baseDomain: string | null | undefined,
): StorefrontHostTarget | null {
  const normalizedHost = normalizeStorefrontHost(host);
  if (!normalizedHost) {
    return null;
  }

  const normalizedBaseDomain = normalizeStorefrontHost(baseDomain);
  const suffix = normalizedBaseDomain ? `.${normalizedBaseDomain}` : "";
  if (suffix && normalizedHost.endsWith(suffix)) {
    const subdomain = normalizedHost.slice(0, -suffix.length);
    if (subdomain && !subdomain.includes(".")) {
      return { type: "subdomain", value: subdomain };
    }
  }

  return { type: "domain", value: normalizedHost };
}
