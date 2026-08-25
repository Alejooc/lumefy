import { resolveStorefront } from "@/lib/storefront-api";

export const dynamic = "force-dynamic";

export async function GET({ params }: { params: Promise<{ path: string[] }> }) {
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
  const target = `${origin}/api/v1/storefront/public/${encodeURIComponent(storefront.id)}/assets/${path.map(encodeURIComponent).join("/")}`;
  const response = await fetch(target, { cache: "no-store" });
  if (!response.ok) return new Response(null, { status: response.status });
  return new Response(response.body, { headers: { "Content-Type": response.headers.get("content-type") || "application/octet-stream", "Cache-Control": "public, max-age=31536000, immutable" } });
}
