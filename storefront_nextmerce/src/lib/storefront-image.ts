export function storefrontImageUrl(value?: string | null): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    if (url.pathname.startsWith("/static/")) {
      return `/media${url.pathname}`;
    }
  } catch {
    // Relative and template-local image paths stay unchanged.
  }
  return value;
}
