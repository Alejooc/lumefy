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
    // Provider catalog images can live behind an authenticated endpoint whose
    // asset base is different from the catalog API base. Route both API-style
    // paths and ordinary image filenames through the same-origin proxy. The
    // proxy falls back to the original URL for public, non-Lumefy assets.
    if (
      url.pathname.includes("/api/external/") ||
      /\.(avif|gif|jpe?g|png|svg|webp|bmp|ico)$/i.test(url.pathname)
    ) {
      return `/external-image?url=${encodeURIComponent(normalized)}`;
    }
  } catch {
    // Relative and template-local image paths stay unchanged.
  }
  return normalized;
}
