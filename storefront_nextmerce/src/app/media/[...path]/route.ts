import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const internalApi = process.env.INTERNAL_API_URL || "http://backend:8000/api/v1";
  const origin = new URL(internalApi).origin;
  const target = `${origin}/${path.map(encodeURIComponent).join("/")}`;
  const response = await fetch(target, { cache: "no-store" });
  if (!response.ok) return new Response(null, { status: response.status });
  return new Response(response.body, { headers: { "Content-Type": response.headers.get("content-type") || "application/octet-stream", "Cache-Control": "public, max-age=3600" } });
}
