import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const sourceUrl = request.nextUrl.searchParams.get("url")?.trim();
  if (!sourceUrl) return new Response(null, { status: 400 });

  const internalApi = (process.env.INTERNAL_API_URL || "http://backend:8000/api/v1").replace(/\/$/, "");
  const target = `${internalApi}/integrations/assets?url=${encodeURIComponent(sourceUrl)}`;
  const response = await fetch(target, { next: { revalidate: 86400 } });
  if (!response.ok) return new Response(null, { status: response.status });

  return new Response(response.body, {
    headers: {
      "Content-Type": response.headers.get("content-type") || "application/octet-stream",
      "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
    },
  });
}
