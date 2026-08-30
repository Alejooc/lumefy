import { NextRequest, NextResponse } from "next/server";
import { getPublicProducts, resolveStorefront } from "@/lib/storefront-api";

export const dynamic = "force-dynamic";

const FORWARDED_PARAMS = [
  "collection",
  "category",
  "brand",
  "q",
  "type",
  "size",
  "color",
  "sort",
  "min_price",
  "max_price",
  "page",
  "page_size",
  "include_facets",
] as const;

/** Server-side proxy used by the storefront's incremental product loader. */
export async function GET(request: NextRequest) {
  try {
    const storefront = await resolveStorefront();
    const params: Record<string, string> = {};
    for (const key of FORWARDED_PARAMS) {
      const value = request.nextUrl.searchParams.get(key);
      if (value) params[key] = value;
    }

    const catalog = await getPublicProducts(storefront.id, params);
    const isPreviewRequest = Boolean(
      request.nextUrl.searchParams.get("preview_token") ||
      request.cookies.get("lumefy_preview_token")?.value,
    );
    const isCollectionRequest = Boolean(params.collection);
    return NextResponse.json(catalog, {
      headers: {
        // Inventory is checked again when an order is created. This lets the
        // public catalog responses be reused briefly at the edge while
        // preview and collection responses remain isolated from the public
        // cache. Collection membership is materialized from automated rules,
        // so a cached incremental batch could otherwise show products that
        // were just removed from the collection.
        "Cache-Control": isPreviewRequest || isCollectionRequest
          ? "private, no-store"
          : "public, max-age=15, s-maxage=15, stale-while-revalidate=30",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "No se pudo cargar el catálogo";
    return NextResponse.json({ detail: message }, { status: 502 });
  }
}
