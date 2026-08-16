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
    // API-style provider paths can require credentials unavailable to the
    // browser. Public CDN/image-base URLs stay direct so Next's optimizer can
    // fetch them normally (the admin panel uses this same public URL).
    if (url.pathname.includes("/api/external/")) {
      return `/external-image?url=${encodeURIComponent(normalized)}`;
    }
  } catch {
    // Relative and template-local image paths stay unchanged.
  }
  return normalized;
}
