import type { NextRequest } from "next/server";

import { resolveStorefront } from "@/lib/storefront-api";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  if (
    path.length < 2 ||
    path[0] !== "static" ||
    path.some((segment) => segment === "." || segment === ".." || segment.includes("\\"))
  ) {
    return new Response(null, { status: 404 });
  }
  let storefront;
  try {
    storefront = await resolveStorefront();
  } catch {
    return new Response(null, { status: 404 });
  }
  const internalApi = process.env.INTERNAL_API_URL || "http://backend:8000/api/v1";
  const origin = new URL(internalApi).origin;
  const previewToken =
    request.nextUrl.searchParams.get("preview_token") ||
    request.cookies.get("lumefy_preview_token")?.value;
  const targetUrl = new URL(
    `${origin}/api/v1/storefront/public/${encodeURIComponent(storefront.id)}/assets/${path.map(encodeURIComponent).join("/")}`,
  );
  if (previewToken) targetUrl.searchParams.set("preview_token", previewToken);
  const target = targetUrl.toString();
  const response = await fetch(target, { cache: "no-store" });
  if (!response.ok) return new Response(null, { status: response.status });
  return new Response(response.body, {
    headers: {
      "Content-Type": response.headers.get("content-type") || "application/octet-stream",
      "Cache-Control": previewToken ? "private, no-store" : "public, max-age=31536000, immutable",
    },
  });
}
