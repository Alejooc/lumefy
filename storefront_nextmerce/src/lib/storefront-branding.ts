import {
  PublicStorefront,
  PublicStorefrontBrandingPromo,
} from "@/types/storefront";
import { storefrontImageUrl } from "./storefront-image";

export type StorefrontBrandingViewModel = {
  logoUrl?: string;
  mobileLogoUrl?: string;
  logoAlt: string;
  faviconUrl?: string;
  supportPhone: string;
  supportEmail: string;
  supportAddress: string;
  website?: string;
  footerText: string;
  announcement: {
    enabled: boolean;
    text: string;
    href?: string;
    backgroundColor: string;
    textColor: string;
  };
  header: {
    supportLabel: string;
    searchPlaceholder: string;
    accountHeading: string;
    guestAccountLabel: string;
    signOutLabel: string;
    cartHeading: string;
    recentlyViewedLabel: string;
    wishlistLabel: string;
    backgroundColor: string;
    textColor: string;
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
    backgroundColor: string;
    textColor: string;
    bottomBackgroundColor: string;
  };
  socialLinks: Array<{
    key: "facebook" | "twitter" | "instagram" | "linkedin";
    href: string;
  }>;
  promoBanners: PublicStorefrontBrandingPromo[];
  buttonLabels: StorefrontButtonLabels;
};

export type StorefrontButtonLabels = {
  addToCart: string;
  selectOptions: string;
  soldOut: string;
  viewCart: string;
  goToCheckout: string;
  applyCoupon: string;
  updateCoupon: string;
  checkout: string;
  signIn: string;
  clearFilters: string;
  applyPrice: string;
  applyCode: string;
  quickView: string;
  addToWishlist: string;
  loginToWishlist: string;
};

export type StorefrontThemeStyleViewModel = {
  primaryColor: string;
  accentColor: string;
  pageBackgroundColor: string;
  bodyTextColor: string;
  headingTextColor: string;
  bodyFont: string;
  headingFont: string;
  contentWidth: number;
  cornerRadius: string;
  navigationStyle: "standard" | "minimal";
  navigationVariant: "underline" | "pill" | "plain";
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
const DEFAULT_HEADER_BACKGROUND = "#FFFFFF";
const DEFAULT_HEADER_TEXT = "#1C274C";
const DEFAULT_FOOTER_BACKGROUND = "#FFFFFF";
const DEFAULT_FOOTER_TEXT = "#1C274C";
const DEFAULT_FOOTER_BOTTOM_BACKGROUND = "#F3F4F6";
const DEFAULT_ANNOUNCEMENT_BACKGROUND = "#1C274C";
const DEFAULT_ANNOUNCEMENT_TEXT = "#FFFFFF";
const DEFAULT_PRIMARY_COLOR = "#3C50E0";
const DEFAULT_ACCENT_COLOR = "#B65332";
const DEFAULT_PAGE_BACKGROUND = "#FFFFFF";
const DEFAULT_BODY_TEXT = "#5D6881";
const DEFAULT_HEADING_TEXT = "#1C274C";
const DEFAULT_BODY_FONT = '"Euclid Circular A", sans-serif';
const DEFAULT_HEADING_FONT = '"Euclid Circular A", sans-serif';
const DEFAULT_CONTENT_WIDTH = 1170;
const DEFAULT_CORNER_RADIUS = "0.75rem";
const DEFAULT_BUTTON_LABELS: StorefrontButtonLabels = {
  addToCart: "Agregar al carrito",
  selectOptions: "Elegir opciones",
  soldOut: "Agotado",
  viewCart: "Ver carrito",
  goToCheckout: "Ir al pago",
  applyCoupon: "Aplicar cupón",
  updateCoupon: "Actualizar cupón",
  checkout: "Finalizar compra",
  signIn: "Iniciar sesión",
  clearFilters: "Limpiar filtros",
  applyPrice: "Aplicar precio",
  applyCode: "Aplicar código",
  quickView: "Vista rápida",
  addToWishlist: "Agregar a favoritos",
  loginToWishlist: "Inicia sesión para guardar favoritos",
};

function nonEmpty(value: string | null | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized || undefined;
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function explicitSetting(
  sources: Array<Record<string, unknown>>,
  key: string,
): { present: boolean; value: unknown } {
  for (const source of sources) {
    if (Object.prototype.hasOwnProperty.call(source, key)) {
      return { present: true, value: source[key] };
    }
  }
  return { present: false, value: undefined };
}

function stringSetting(
  setting: { present: boolean; value: unknown },
  fallback: string | undefined,
): string | undefined {
  if (setting.present) {
    return typeof setting.value === "string" ? setting.value.trim() : undefined;
  }
  return nonEmpty(fallback);
}

function safeHexColor(value: unknown, fallback: string): string {
  const normalized = typeof value === "string" ? value.trim() : "";
  return /^#[0-9a-f]{6}$/i.test(normalized) ? normalized : fallback;
}

function validHref(value: unknown): string | undefined {
  const normalized = typeof value === "string" ? value.trim() : "";
  if (/^\/(?!\/)/.test(normalized) || /^https?:\/\//i.test(normalized)) {
    return normalized;
  }
  return undefined;
}

function fontFamily(value: unknown, fallback: string): string {
  switch (value) {
    case "euclid":
      return '"Euclid Circular A", sans-serif';
    case "editorial":
      return "Georgia, serif";
    case "humanist":
      return '"Trebuchet MS", sans-serif';
    default:
      return fallback;
  }
}

function normalizeButtonLabels(sources: Record<string, unknown>[]): StorefrontButtonLabels {
  const valueFor = (key: string, fallback: string): string => {
    const setting = explicitSetting(sources, key);
    return setting.present && typeof setting.value === "string" && setting.value.trim()
      ? setting.value.trim()
      : fallback;
  };

  return {
    addToCart: valueFor("add_to_cart", DEFAULT_BUTTON_LABELS.addToCart),
    selectOptions: valueFor("select_options", DEFAULT_BUTTON_LABELS.selectOptions),
    soldOut: valueFor("sold_out", DEFAULT_BUTTON_LABELS.soldOut),
    viewCart: valueFor("view_cart", DEFAULT_BUTTON_LABELS.viewCart),
    goToCheckout: valueFor("go_to_checkout", DEFAULT_BUTTON_LABELS.goToCheckout),
    applyCoupon: valueFor("apply_coupon", DEFAULT_BUTTON_LABELS.applyCoupon),
    updateCoupon: valueFor("update_coupon", DEFAULT_BUTTON_LABELS.updateCoupon),
    checkout: valueFor("checkout", DEFAULT_BUTTON_LABELS.checkout),
    signIn: valueFor("sign_in", DEFAULT_BUTTON_LABELS.signIn),
    clearFilters: valueFor("clear_filters", DEFAULT_BUTTON_LABELS.clearFilters),
    applyPrice: valueFor("apply_price", DEFAULT_BUTTON_LABELS.applyPrice),
    applyCode: valueFor("apply_code", DEFAULT_BUTTON_LABELS.applyCode),
    quickView: valueFor("quick_view", DEFAULT_BUTTON_LABELS.quickView),
    addToWishlist: valueFor("add_to_wishlist", DEFAULT_BUTTON_LABELS.addToWishlist),
    loginToWishlist: valueFor("login_to_wishlist", DEFAULT_BUTTON_LABELS.loginToWishlist),
  };
}

export function getStorefrontButtonLabelsFromSettings(value: unknown): StorefrontButtonLabels {
  const settings = objectValue(value);
  const globalSettings = objectValue(settings["global"]);
  return normalizeButtonLabels([
    objectValue(settings["buttons"]),
    objectValue(globalSettings["buttons"]),
  ]);
}

function cornerRadius(value: unknown): string {
  switch (value) {
    case "sharp":
      return "0.25rem";
    case "round":
      return "1.5rem";
    case "soft":
      return DEFAULT_CORNER_RADIUS;
    default:
      return DEFAULT_CORNER_RADIUS;
  }
}

function contentWidth(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? Math.min(1440, Math.max(960, Math.round(parsed))) : DEFAULT_CONTENT_WIDTH;
}

function navigationVariant(value: unknown): "underline" | "pill" | "plain" {
  return value === "pill" || value === "plain" ? value : "underline";
}

function themeStylesFromSettings(
  legacySettings: unknown,
  documentSettings: unknown,
): StorefrontThemeStyleViewModel {
  const legacy = objectValue(legacySettings);
  const legacyGlobal = objectValue(legacy["global"]);
  const document = objectValue(documentSettings);
  const documentGlobal = objectValue(document["global"]);
  const styles = {
    ...objectValue(legacy["styles"]),
    ...objectValue(legacyGlobal["styles"]),
    ...objectValue(document["styles"]),
    ...objectValue(documentGlobal["styles"]),
  };

  return {
    primaryColor: safeHexColor(styles["primary_color"], DEFAULT_PRIMARY_COLOR),
    accentColor: safeHexColor(styles["accent_color"], DEFAULT_ACCENT_COLOR),
    pageBackgroundColor: safeHexColor(styles["page_background_color"], DEFAULT_PAGE_BACKGROUND),
    bodyTextColor: safeHexColor(styles["body_text_color"], DEFAULT_BODY_TEXT),
    headingTextColor: safeHexColor(styles["heading_text_color"], DEFAULT_HEADING_TEXT),
    bodyFont: fontFamily(styles["body_font"], DEFAULT_BODY_FONT),
    headingFont: fontFamily(styles["heading_font"], DEFAULT_HEADING_FONT),
    contentWidth: contentWidth(styles["content_width"]),
    cornerRadius: cornerRadius(styles["corner_radius"]),
    navigationStyle: styles["navigation_style"] === "minimal" ? "minimal" : "standard",
    navigationVariant: navigationVariant(styles["navigation_variant"]),
  };
}

export function getStorefrontThemeStyles(
  storefront: PublicStorefront | null | undefined,
): StorefrontThemeStyleViewModel {
  const themeDocument = objectValue(storefront?.theme_document);
  return themeStylesFromSettings(storefront?.theme_settings, themeDocument["settings"]);
}

export function getThemeStylesFromDocumentSettings(value: unknown): StorefrontThemeStyleViewModel {
  return themeStylesFromSettings({}, value);
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
      href: nonEmpty(String(item["href"] || "")) || "",
    }))
    .filter((item) => item.label && (/^\//.test(item.href) || /^https?:\/\//i.test(item.href)));
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
  const themeSettings =
    storefront?.theme_settings && typeof storefront.theme_settings === "object"
      ? (storefront.theme_settings as Record<string, unknown>)
      : {};
  const themeDocument = objectValue(storefront?.theme_document);
  const documentSettings = objectValue(themeDocument["settings"]);
  const legacyGlobalSettings = objectValue(themeSettings["global"]);
  const documentGlobalSettings = objectValue(documentSettings["global"]);
  const buttonSettings = [
    objectValue(themeSettings["buttons"]),
    objectValue(legacyGlobalSettings["buttons"]),
    objectValue(documentSettings["buttons"]),
    objectValue(documentGlobalSettings["buttons"]),
  ];
  const brandingSettings = {
    ...objectValue(themeSettings["branding"]),
    ...objectValue(legacyGlobalSettings["branding"]),
    ...objectValue(documentSettings["branding"]),
    ...objectValue(documentGlobalSettings["branding"]),
  };
  const documentBrandingSettings = [
    objectValue(documentGlobalSettings["branding"]),
    objectValue(documentSettings["branding"]),
  ];
  const headerSettings = {
    ...objectValue(themeSettings["header"]),
    ...objectValue(legacyGlobalSettings["header"]),
    ...objectValue(documentSettings["header"]),
    ...objectValue(documentGlobalSettings["header"]),
  };
  const footerSettings = {
    ...objectValue(themeSettings["footer"]),
    ...objectValue(legacyGlobalSettings["footer"]),
    ...objectValue(documentSettings["footer"]),
    ...objectValue(documentGlobalSettings["footer"]),
  };
  const documentFooterSettings = [
    objectValue(documentGlobalSettings["footer"]),
    objectValue(documentSettings["footer"]),
  ];
  const documentSocialSettings = documentFooterSettings.map((footer) =>
    objectValue(footer["social_links"]),
  );
  const legacySocialLinks = {
    ...objectValue(themeSettings["social_links"]),
    ...objectValue(legacyGlobalSettings["social_links"]),
    ...objectValue(objectValue(themeSettings["branding"])["social_links"]),
    ...objectValue(objectValue(legacyGlobalSettings["branding"])["social_links"]),
    ...objectValue(objectValue(themeSettings["footer"])["social_links"]),
    ...objectValue(objectValue(legacyGlobalSettings["footer"])["social_links"]),
  };
  const socialSetting = (key: string): { present: boolean; value: unknown } =>
    explicitSetting(documentSocialSettings, key);
  const social = {
    facebook: stringSetting(
      socialSetting("facebook"),
      nonEmpty(String(legacySocialLinks["facebook"] || "")) || nonEmpty(branding?.social_links?.facebook),
    ),
    instagram: stringSetting(
      socialSetting("instagram"),
      nonEmpty(String(legacySocialLinks["instagram"] || "")) || nonEmpty(branding?.social_links?.instagram),
    ),
    twitter: stringSetting(
      socialSetting("twitter"),
      nonEmpty(String(legacySocialLinks["twitter"] || "")) || nonEmpty(branding?.social_links?.twitter),
    ),
    linkedin: stringSetting(
      socialSetting("linkedin"),
      nonEmpty(String(legacySocialLinks["linkedin"] || "")) || nonEmpty(branding?.social_links?.linkedin),
    ),
  };
  const announcementSettings = {
    ...objectValue(themeSettings["announcement"]),
    ...objectValue(legacyGlobalSettings["announcement"]),
    ...objectValue(documentSettings["announcement"]),
    ...objectValue(documentGlobalSettings["announcement"]),
  };
  const storeName = storefront?.name?.trim() || "Tienda online";
  const announcementText = nonEmpty(String(announcementSettings["text"] || "")) || "";
  const logoSetting = explicitSetting(documentBrandingSettings, "logo_url");
  const faviconSetting = explicitSetting(documentBrandingSettings, "favicon_url");
  const legacyLogoUrl =
    nonEmpty(String(brandingSettings["logo_url"] || "")) ||
    nonEmpty(String(themeSettings["logo_url"] || "")) ||
    nonEmpty(branding?.logo_url);
  const legacyFaviconUrl =
    nonEmpty(String(brandingSettings["favicon_url"] || "")) ||
    nonEmpty(String(themeSettings["favicon_url"] || ""));
  const mobileLogoSetting = explicitSetting(documentBrandingSettings, "mobile_logo_url");
  const legacyMobileLogoUrl =
    nonEmpty(String(brandingSettings["mobile_logo_url"] || "")) ||
    nonEmpty(String(themeSettings["mobile_logo_url"] || "")) ||
    nonEmpty(String(objectValue(branding)["mobile_logo_url"] || ""));
  const supportPhoneSetting = explicitSetting(documentFooterSettings, "support_phone");
  const supportEmailSetting = explicitSetting(documentFooterSettings, "support_email");
  const supportAddressSetting = explicitSetting(documentFooterSettings, "support_address");
  const footerTextSetting = explicitSetting(documentFooterSettings, "footer_text");

  return {
    logoUrl: storefrontImageUrl(
      logoSetting.present
        ? (typeof logoSetting.value === "string" ? logoSetting.value.trim() : "")
        : legacyLogoUrl,
    ),
    mobileLogoUrl: storefrontImageUrl(
      mobileLogoSetting.present
        ? (typeof mobileLogoSetting.value === "string" ? mobileLogoSetting.value.trim() : "")
        : legacyMobileLogoUrl,
    ),
    logoAlt: nonEmpty(String(brandingSettings["logo_alt"] || "")) || storeName,
    faviconUrl: storefrontImageUrl(
      faviconSetting.present
        ? (typeof faviconSetting.value === "string" ? faviconSetting.value.trim() : "")
        : legacyFaviconUrl,
    ),
    supportPhone:
      stringSetting(supportPhoneSetting, undefined) ??
      (nonEmpty(String(footerSettings["support_phone"] || "")) ||
        nonEmpty(branding?.support_phone) ||
        DEFAULT_SUPPORT_PHONE),
    supportEmail:
      stringSetting(supportEmailSetting, undefined) ??
      (nonEmpty(String(footerSettings["support_email"] || "")) ||
        nonEmpty(branding?.support_email) ||
        DEFAULT_SUPPORT_EMAIL),
    supportAddress:
      stringSetting(supportAddressSetting, undefined) ??
      (nonEmpty(String(footerSettings["support_address"] || "")) ||
        nonEmpty(branding?.support_address) ||
        DEFAULT_SUPPORT_ADDRESS),
    website: nonEmpty(branding?.website),
    footerText:
      stringSetting(footerTextSetting, undefined) ??
      (nonEmpty(String(footerSettings["footer_text"] || "")) ||
        nonEmpty(branding?.footer_text) ||
        `${storeName}. Todos los derechos reservados.`),
    announcement: {
      enabled: announcementSettings["enabled"] === true && Boolean(announcementText),
      text: announcementText,
      href: validHref(announcementSettings["href"]),
      backgroundColor: safeHexColor(
        announcementSettings["background_color"],
        DEFAULT_ANNOUNCEMENT_BACKGROUND,
      ),
      textColor: safeHexColor(announcementSettings["text_color"], DEFAULT_ANNOUNCEMENT_TEXT),
    },
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
      backgroundColor: safeHexColor(
        headerSettings["background_color"],
        DEFAULT_HEADER_BACKGROUND,
      ),
      textColor: safeHexColor(headerSettings["text_color"], DEFAULT_HEADER_TEXT),
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
      backgroundColor: safeHexColor(
        footerSettings["background_color"],
        DEFAULT_FOOTER_BACKGROUND,
      ),
      textColor: safeHexColor(footerSettings["text_color"], DEFAULT_FOOTER_TEXT),
      bottomBackgroundColor: safeHexColor(
        footerSettings["bottom_background_color"],
        DEFAULT_FOOTER_BOTTOM_BACKGROUND,
      ),
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
    buttonLabels: normalizeButtonLabels(buttonSettings),
  };
}
