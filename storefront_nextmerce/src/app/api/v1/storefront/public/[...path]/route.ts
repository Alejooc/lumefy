import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "keep-alive",
  "transfer-encoding",
  "upgrade",
]);

function backendUrl(path: string[], request: NextRequest): string {
  const internalApi = (process.env.INTERNAL_API_URL || "http://backend:8000/api/v1").replace(/\/+$/, "");
  const target = new URL(`${internalApi}/storefront/public/${path.map(encodeURIComponent).join("/")}`);
  request.nextUrl.searchParams.forEach((value, key) => target.searchParams.append(key, value));
  return target.toString();
}

async function proxyPublicApi(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  if (!path.length || path.some((segment) => segment === "." || segment === ".." || segment.includes("\\"))) {
    return NextResponse.json({ detail: "Ruta pública inválida" }, { status: 404 });
  }

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  headers.delete("connection");

  const method = request.method.toUpperCase();
  const body = method === "GET" || method === "HEAD" || method === "OPTIONS"
    ? undefined
    : await request.arrayBuffer();

  try {
    const upstream = await fetch(backendUrl(path, request), {
      method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
    });
    const responseHeaders = new Headers();
    upstream.headers.forEach((value, key) => {
      if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) responseHeaders.set(key, value);
    });
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json({ detail: "No se pudo contactar al backend" }, { status: 502 });
  }
}

export const GET = proxyPublicApi;
export const HEAD = proxyPublicApi;
export const OPTIONS = proxyPublicApi;
export const POST = proxyPublicApi;
export const PUT = proxyPublicApi;
export const PATCH = proxyPublicApi;
export const DELETE = proxyPublicApi;
