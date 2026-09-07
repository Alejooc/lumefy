import type { NextRequest } from "next/server";
import sharp from "sharp";

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

  const contentType = response.headers.get("content-type") || "application/octet-stream";
  const width = Number.parseInt(request.nextUrl.searchParams.get("w") || "", 10);
  const qualityParam = Number.parseInt(request.nextUrl.searchParams.get("q") || "75", 10);
  const quality = Number.isFinite(qualityParam) ? Math.min(Math.max(qualityParam, 40), 85) : 75;
  const canOptimize =
    Number.isFinite(width) &&
    width > 0 &&
    width <= 2400 &&
    contentType.startsWith("image/") &&
    !["image/svg+xml", "image/gif"].includes(contentType.split(";")[0].trim().toLowerCase());

  if (canOptimize) {
    const source = Buffer.from(await response.arrayBuffer());
    try {
      const optimized = await sharp(source, { failOn: "none" })
        .rotate()
        .resize({ width, withoutEnlargement: true })
        .webp({ quality })
        .toBuffer();

      return new Response(optimized, {
        headers: {
          "Content-Type": "image/webp",
          "Content-Length": String(optimized.byteLength),
          "Cache-Control": previewToken ? "private, no-store" : "public, max-age=31536000, immutable",
        },
      });
    } catch {
      // If an unusual but valid image cannot be decoded, preserve the original
      // response rather than making the storefront image disappear.
      return new Response(source, {
        headers: {
          "Content-Type": contentType,
          "Cache-Control": previewToken ? "private, no-store" : "public, max-age=31536000, immutable",
        },
      });
    }
  }

  return new Response(response.body, {
    headers: {
      "Content-Type": contentType,
      "Cache-Control": previewToken ? "private, no-store" : "public, max-age=31536000, immutable",
    },
  });
}
