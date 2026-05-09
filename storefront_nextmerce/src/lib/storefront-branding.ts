import {
  PublicStorefront,
  PublicStorefrontBrandingPromo,
} from "@/types/storefront";

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

const DEFAULT_SUPPORT_PHONE = "(+965) 7492-3477";
const DEFAULT_SUPPORT_EMAIL = "support@example.com";
const DEFAULT_SUPPORT_ADDRESS =
  "685 Market Street,Las Vegas, LA 95820,United States.";
const DEFAULT_ACCOUNT_LINKS = [
  { href: "/account", label: "My Account" },
  { href: "/login", label: "Login / Register" },
  { href: "/cart", label: "Cart" },
  { href: "/wishlist", label: "Wishlist" },
  { href: "/products", label: "Shop" },
];
const DEFAULT_QUICK_LINKS = [
  { href: "/products", label: "Privacy Policy" },
  { href: "/products", label: "Refund Policy" },
  { href: "/products", label: "Terms of Use" },
  { href: "/products", label: "FAQs" },
  { href: "/contact", label: "Contact" },
];
const DEFAULT_PAYMENT_METHODS = [
  { iconUrl: "/images/payment/payment-01.svg", label: "Visa" },
  { iconUrl: "/images/payment/payment-02.svg", label: "PayPal" },
  { iconUrl: "/images/payment/payment-03.svg", label: "Mastercard" },
  { iconUrl: "/images/payment/payment-04.svg", label: "Apple Pay" },
  { iconUrl: "/images/payment/payment-05.svg", label: "Google Pay" },
];

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
      iconUrl: nonEmpty(String(item["icon_url"] || "")),
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
  const storeName = storefront?.name?.trim() || "NextMerce";

  return {
    logoUrl: nonEmpty(branding?.logo_url),
    supportPhone: nonEmpty(branding?.support_phone) || DEFAULT_SUPPORT_PHONE,
    supportEmail: nonEmpty(branding?.support_email) || DEFAULT_SUPPORT_EMAIL,
    supportAddress:
      nonEmpty(branding?.support_address) || DEFAULT_SUPPORT_ADDRESS,
    website: nonEmpty(branding?.website),
    footerText:
      nonEmpty(branding?.footer_text) || `${storeName}. All rights reserved.`,
    header: {
      supportLabel: nonEmpty(String(headerSettings["support_label"] || "")) || "24/7 SUPPORT",
      searchPlaceholder:
        nonEmpty(String(headerSettings["search_placeholder"] || "")) || "I am shopping for...",
      accountHeading: nonEmpty(String(headerSettings["account_heading"] || "")) || "account",
      guestAccountLabel:
        nonEmpty(String(headerSettings["guest_account_label"] || "")) || "Sign In",
      signOutLabel: nonEmpty(String(headerSettings["sign_out_label"] || "")) || "Sign Out",
      cartHeading: nonEmpty(String(headerSettings["cart_heading"] || "")) || "cart",
      recentlyViewedLabel:
        nonEmpty(String(headerSettings["recently_viewed_label"] || "")) || "Recently Viewed",
      wishlistLabel: nonEmpty(String(headerSettings["wishlist_label"] || "")) || "Wishlist",
    },
    footer: {
      helpTitle: nonEmpty(String(footerSettings["help_title"] || "")) || "Help & Support",
      accountTitle: nonEmpty(String(footerSettings["account_title"] || "")) || "Account",
      quickLinksTitle:
        nonEmpty(String(footerSettings["quick_links_title"] || "")) || "Quick Link",
      appTitle: nonEmpty(String(footerSettings["app_title"] || "")) || "Download App",
      appDescription:
        nonEmpty(String(footerSettings["app_description"] || "")) ||
        "Exclusive savings for app users",
      appStoreSubtitle:
        nonEmpty(String(footerSettings["app_store_subtitle"] || "")) || "Download on the",
      appStoreLabel: nonEmpty(String(footerSettings["app_store_label"] || "")) || "App Store",
      appStoreUrl: nonEmpty(String(footerSettings["app_store_url"] || "")),
      playStoreSubtitle:
        nonEmpty(String(footerSettings["play_store_subtitle"] || "")) || "Get it on",
      playStoreLabel:
        nonEmpty(String(footerSettings["play_store_label"] || "")) || "Google Play",
      playStoreUrl: nonEmpty(String(footerSettings["play_store_url"] || "")),
      paymentTitle: nonEmpty(String(footerSettings["payment_title"] || "")) || "We Accept:",
      showSocialLinks: footerSettings["show_social_links"] !== false,
      showAppDownloads: footerSettings["show_app_downloads"] !== false,
      showPaymentMethods: footerSettings["show_payment_methods"] !== false,
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
    promoBanners: (branding?.promo_banners ?? []).filter(validPromoBanner),
  };
}
