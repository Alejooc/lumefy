import {
  PublicStorefront,
  PublicStorefrontBrandingPromo,
} from "@/types/storefront";
import { storefrontImageUrl } from "./storefront-image";

export type StorefrontBrandingViewModel = {
  logoUrl?: string;
  supportPhone: string;
  supportEmail: string;
  supportAddress: string;
  website?: string;
  footerText: string;
  header: {
    supportLabel: string;
    searchPlaceholder: string;
    accountHeading: string;
    guestAccountLabel: string;
    signOutLabel: string;
    cartHeading: string;
    recentlyViewedLabel: string;
    wishlistLabel: string;
  };
  footer: {
    helpTitle: string;
    accountTitle: string;
    quickLinksTitle: string;
    appTitle: string;
    appDescription: string;
    appStoreSubtitle: string;
    appStoreLabel: string;
    appStoreUrl?: string;
    playStoreSubtitle: string;
    playStoreLabel: string;
    playStoreUrl?: string;
    paymentTitle: string;
    showSocialLinks: boolean;
    showAppDownloads: boolean;
    showPaymentMethods: boolean;
    accountLinks: Array<{ label: string; href: string }>;
    quickLinks: Array<{ label: string; href: string }>;
    paymentMethods: Array<{ label: string; href?: string; iconUrl?: string }>;
  };
  socialLinks: Array<{
    key: "facebook" | "twitter" | "instagram" | "linkedin";
    href: string;
  }>;
  promoBanners: PublicStorefrontBrandingPromo[];
};

const DEFAULT_SUPPORT_PHONE = "";
const DEFAULT_SUPPORT_EMAIL = "";
const DEFAULT_SUPPORT_ADDRESS = "";
const DEFAULT_ACCOUNT_LINKS = [
  { href: "/account", label: "Mi cuenta" },
  { href: "/login", label: "Ingresar" },
  { href: "/cart", label: "Carrito" },
  { href: "/wishlist", label: "Favoritos" },
  { href: "/products", label: "Productos" },
];
const DEFAULT_QUICK_LINKS = [
  { href: "/products", label: "Productos" },
  { href: "/contact", label: "Contacto" },
];
const DEFAULT_PAYMENT_METHODS: Array<{ label: string; href?: string; iconUrl?: string }> = [];

function nonEmpty(value: string | null | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized || undefined;
}

function validPromoBanner(
  banner: PublicStorefrontBrandingPromo | null | undefined,
): banner is PublicStorefrontBrandingPromo {
  return Boolean(banner?.id && banner.title);
}

function validLinkList(input: unknown): Array<{ label: string; href: string }> {
  if (!Array.isArray(input)) {
    return [];
  }
  return input
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => ({
      label: nonEmpty(String(item["label"] || "")) || "",
      href: nonEmpty(String(item["href"] || "")) || "#",
    }))
    .filter((item) => item.label);
}

function validPaymentList(
  input: unknown,
): Array<{ label: string; href?: string; iconUrl?: string }> {
  if (!Array.isArray(input)) {
    return [];
  }
  return input
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => ({
      label: nonEmpty(String(item["label"] || "")) || "",
      href: nonEmpty(String(item["href"] || "")),
      iconUrl: storefrontImageUrl(nonEmpty(String(item["icon_url"] || ""))),
    }))
    .filter((item) => item.label || item.iconUrl);
}

export function getStorefrontBranding(
  storefront: PublicStorefront | null | undefined,
): StorefrontBrandingViewModel {
  const branding = storefront?.branding;
  const social = branding?.social_links ?? {};
  const themeSettings =
    storefront?.theme_settings && typeof storefront.theme_settings === "object"
      ? (storefront.theme_settings as Record<string, unknown>)
      : {};
  const headerSettings =
    themeSettings["header"] && typeof themeSettings["header"] === "object"
      ? (themeSettings["header"] as Record<string, unknown>)
      : {};
  const footerSettings =
    themeSettings["footer"] && typeof themeSettings["footer"] === "object"
      ? (themeSettings["footer"] as Record<string, unknown>)
      : {};
  const storeName = storefront?.name?.trim() || "Tienda online";

  return {
    logoUrl: storefrontImageUrl(branding?.logo_url),
    supportPhone: nonEmpty(branding?.support_phone) || DEFAULT_SUPPORT_PHONE,
    supportEmail: nonEmpty(branding?.support_email) || DEFAULT_SUPPORT_EMAIL,
    supportAddress:
      nonEmpty(branding?.support_address) || DEFAULT_SUPPORT_ADDRESS,
    website: nonEmpty(branding?.website),
    footerText:
      nonEmpty(branding?.footer_text) || `${storeName}. Todos los derechos reservados.`,
    header: {
      supportLabel: nonEmpty(String(headerSettings["support_label"] || "")) || "Atención al cliente",
      searchPlaceholder:
        nonEmpty(String(headerSettings["search_placeholder"] || "")) || "Buscar productos...",
      accountHeading: nonEmpty(String(headerSettings["account_heading"] || "")) || "cuenta",
      guestAccountLabel:
        nonEmpty(String(headerSettings["guest_account_label"] || "")) || "Ingresar",
      signOutLabel: nonEmpty(String(headerSettings["sign_out_label"] || "")) || "Cerrar sesión",
      cartHeading: nonEmpty(String(headerSettings["cart_heading"] || "")) || "carrito",
      recentlyViewedLabel:
        nonEmpty(String(headerSettings["recently_viewed_label"] || "")) || "Vistos recientemente",
      wishlistLabel: nonEmpty(String(headerSettings["wishlist_label"] || "")) || "Favoritos",
    },
    footer: {
      helpTitle: nonEmpty(String(footerSettings["help_title"] || "")) || "Ayuda y contacto",
      accountTitle: nonEmpty(String(footerSettings["account_title"] || "")) || "Cuenta",
      quickLinksTitle:
        nonEmpty(String(footerSettings["quick_links_title"] || "")) || "Enlaces",
      appTitle: nonEmpty(String(footerSettings["app_title"] || "")) || "App móvil",
      appDescription:
        nonEmpty(String(footerSettings["app_description"] || "")) ||
        "Compra desde cualquier lugar",
      appStoreSubtitle:
        nonEmpty(String(footerSettings["app_store_subtitle"] || "")) || "Disponible en",
      appStoreLabel: nonEmpty(String(footerSettings["app_store_label"] || "")) || "App Store",
      appStoreUrl: nonEmpty(String(footerSettings["app_store_url"] || "")),
      playStoreSubtitle:
        nonEmpty(String(footerSettings["play_store_subtitle"] || "")) || "Disponible en",
      playStoreLabel:
        nonEmpty(String(footerSettings["play_store_label"] || "")) || "Google Play",
      playStoreUrl: nonEmpty(String(footerSettings["play_store_url"] || "")),
      paymentTitle: nonEmpty(String(footerSettings["payment_title"] || "")) || "Medios de pago:",
      showSocialLinks: footerSettings["show_social_links"] === true,
      showAppDownloads: footerSettings["show_app_downloads"] === true,
      showPaymentMethods: footerSettings["show_payment_methods"] === true,
      accountLinks: validLinkList(footerSettings["account_links"]).length
        ? validLinkList(footerSettings["account_links"])
        : DEFAULT_ACCOUNT_LINKS,
      quickLinks: validLinkList(footerSettings["quick_links"]).length
        ? validLinkList(footerSettings["quick_links"])
        : DEFAULT_QUICK_LINKS,
      paymentMethods: validPaymentList(footerSettings["payment_methods"]).length
        ? validPaymentList(footerSettings["payment_methods"])
        : DEFAULT_PAYMENT_METHODS,
    },
    socialLinks: (["facebook", "twitter", "instagram", "linkedin"] as const)
      .map((key) => ({ key, href: nonEmpty(social[key]) }))
      .filter(
        (entry): entry is { key: "facebook" | "twitter" | "instagram" | "linkedin"; href: string } =>
          Boolean(entry.href),
      ),
    promoBanners: (branding?.promo_banners ?? [])
      .filter(validPromoBanner)
      .map((banner) => ({
        ...banner,
        image_url: storefrontImageUrl(banner.image_url),
      })),
  };
}
