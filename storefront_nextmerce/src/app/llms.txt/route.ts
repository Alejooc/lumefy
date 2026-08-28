import { NextRequest } from "next/server";

import { getPublicCollections, getPublicProducts, resolveStorefront } from "@/lib/storefront-api";
import { getSiteUrl, stripHtml } from "@/lib/seo";
import { getStorefrontBranding } from "@/lib/storefront-branding";

export const dynamic = "force-dynamic";

const LLM_PRODUCT_LIMIT = 48;

function cleanLine(value: unknown, maxLength = 320): string {
  return stripHtml(typeof value === "string" ? value : "")
    .replace(/[\r\n]+/g, " ")
    .replace(/[\[\]]/g, "")
    .trim()
    .slice(0, maxLength);
}

function absoluteUrl(siteUrl: string, path: string): string {
  return new URL(path, `${siteUrl.replace(/\/$/, "")}/`).toString();
}

function hasPreviewRequest(request: NextRequest): boolean {
  return Boolean(
    request.nextUrl.searchParams.get("preview_token") ||
      request.cookies.get("lumefy_preview_token")?.value,
  );
}

export async function GET(request: NextRequest) {
  const previewRequest = hasPreviewRequest(request);

  try {
    const [storefront, siteUrl] = await Promise.all([resolveStorefront(), getSiteUrl()]);
    const [collections, catalog] = await Promise.all([
      getPublicCollections(storefront.id),
      getPublicProducts(storefront.id, {
        page: 1,
        page_size: LLM_PRODUCT_LIMIT,
        sort: "latest",
        include_facets: "false",
      }),
    ]);
    const branding = getStorefrontBranding(storefront);
    const seoDescription = cleanLine(storefront.seo_settings?.meta_description);
    const lines = [
      `# ${cleanLine(storefront.name, 120) || "Tienda online"}`,
      "",
      `> ${seoDescription || `Catálogo y compras online de ${cleanLine(storefront.name, 120) || "la tienda"}.`}`,
      "",
      "Este archivo resume el contenido público y las páginas principales de la tienda.",
      "Usa las páginas enlazadas como fuente canónica para consultar detalles actuales.",
      "",
      "## Sitio oficial",
      `- Inicio: ${absoluteUrl(siteUrl, "/")}`,
      `- Productos: ${absoluteUrl(siteUrl, "/products")}`,
      `- Contacto: ${absoluteUrl(siteUrl, "/contact")}`,
    ];

    if (branding.supportAddress || branding.supportPhone || branding.supportEmail) {
      lines.push("", "## Contacto");
      if (branding.supportAddress) lines.push(`- Dirección: ${cleanLine(branding.supportAddress, 180)}`);
      if (branding.supportPhone) lines.push(`- Teléfono: ${cleanLine(branding.supportPhone, 80)}`);
      if (branding.supportEmail) lines.push(`- Correo: ${cleanLine(branding.supportEmail, 120)}`);
    }

    if (collections.length) {
      lines.push("", "## Colecciones");
      for (const collection of collections) {
        const name = cleanLine(collection.name, 120);
        if (!name) continue;
        const description = cleanLine(collection.description, 240);
        lines.push(
          `- [${name}](${absoluteUrl(siteUrl, `/collections/${encodeURIComponent(collection.slug)}`)})${description ? `: ${description}` : ""}`,
        );
      }
    }

    if (catalog.items.length) {
      lines.push("", "## Productos destacados y novedades");
      for (const product of catalog.items) {
        const title = cleanLine(product.title, 140);
        if (!title) continue;
        lines.push(`- [${title}](${absoluteUrl(siteUrl, `/products/${encodeURIComponent(product.slug)}`)})`);
      }
    }

    if (branding.socialLinks.length) {
      lines.push("", "## Perfiles oficiales");
      for (const social of branding.socialLinks) lines.push(`- ${social.href}`);
    }

    return new Response(`${lines.join("\n")}\n`, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": previewRequest
          ? "private, no-store"
          : "public, max-age=300, s-maxage=900, stale-while-revalidate=86400",
      },
    });
  } catch {
    return new Response(
      "# Storefront\n\nEl catálogo no está disponible temporalmente.\n",
      {
        status: 503,
        headers: {
          "Content-Type": "text/plain; charset=utf-8",
          "Cache-Control": "private, no-store",
        },
      },
    );
  }
}
