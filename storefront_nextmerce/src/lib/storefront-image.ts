export function storefrontImageUrl(value?: string | null): string | undefined {
  const normalized = value?.trim();
  if (!normalized) return undefined;

  // Uploads are stored by the API under /static. The storefront proxies them
  // through its same-origin /media route so Next's image optimizer never
  // asks the public host for a path that only exists inside the backend.
  if (normalized.startsWith("/static/")) {
    return `/media${normalized}`;
  }
  if (normalized.startsWith("static/")) {
    return `/media/${normalized}`;
  }

  try {
    const url = new URL(normalized);
    if (url.pathname.startsWith("/static/")) {
      return `/media${url.pathname}`;
    }
    // Provider catalog images can live behind an authenticated REST endpoint.
    // Keep the API key on the backend instead of exposing it to the browser or
    // asking Next's optimizer to fetch the provider URL without credentials.
    if (url.pathname.includes("/api/external/")) {
      return `/external-image?url=${encodeURIComponent(normalized)}`;
    }
  } catch {
    // Relative and template-local image paths stay unchanged.
  }
  return normalized;
}
