export function previewParentOrigin(): string | null {
  if (typeof document === "undefined" || !document.referrer) return null;
  try {
    return new URL(document.referrer).origin;
  } catch {
    return null;
  }
}

export function isTrustedPreviewMessage(event: MessageEvent): boolean {
  if (typeof window === "undefined" || event.source !== window.parent) return false;
  const expectedParentOrigin = previewParentOrigin();
  return !expectedParentOrigin || event.origin === expectedParentOrigin;
}
