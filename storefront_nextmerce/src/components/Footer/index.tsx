"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";

import type { PublicStorefront } from "@/types/storefront";
import { resolveStorefront } from "@/lib/storefront-api";
import { getStorefrontBranding } from "@/lib/storefront-branding";
import { storefrontImageUrl } from "@/lib/storefront-image";
import { isTrustedPreviewMessage, previewParentOrigin } from "@/lib/preview";

type SocialKey = "facebook" | "twitter" | "instagram" | "linkedin";

function SocialIcon({ name }: { name: string }) {
  const commonProps = {
    width: 17,
    height: 17,
    viewBox: "0 0 16 16",
    fill: "none",
    "aria-hidden": true,
  } as const;

  switch (name) {
    case "facebook":
      return (
        <svg {...commonProps}>
          <path d="M9.35 14V8.7h1.8l.27-2.07H9.35V5.31c0-.6.17-1.01 1.04-1.01h1.12V2.45a15 15 0 0 0-1.63-.08c-1.62 0-2.73.99-2.73 2.8v1.46H5.32V8.7h1.83V14h2.2Z" fill="currentColor" />
        </svg>
      );
    case "instagram":
      return (
        <svg {...commonProps}>
          <rect x="2" y="2" width="12" height="12" rx="3" stroke="currentColor" strokeWidth="1.45" />
          <circle cx="8" cy="8" r="2.85" stroke="currentColor" strokeWidth="1.45" />
          <circle cx="11.65" cy="4.35" r=".85" fill="currentColor" />
        </svg>
      );
    case "twitter":
      return (
        <svg {...commonProps}>
          <path d="M2.25 2h2.94l2.84 3.8L11.42 2h2.33l-4.65 5.35L14 14h-2.94L8.1 9.99 4.46 14H2.13l4.67-5.56L2.25 2Zm3.42 1.54h-.88l6.35 8.92h.88L5.67 3.54Z" fill="currentColor" />
        </svg>
      );
    case "linkedin":
      return (
        <svg {...commonProps}>
          <path d="M3.45 5.95H1.08V14h2.37V5.95ZM2.26 2a1.38 1.38 0 1 0 0 2.76A1.38 1.38 0 0 0 2.26 2ZM14.92 9.39c0-2.43-1.3-3.56-3.04-3.56-1.4 0-2.03.77-2.38 1.31V5.95H7.13V14H9.5V10.01c0-1.05.2-2.07 1.5-2.07 1.29 0 1.3 1.2 1.3 2.14V14h2.37l.25-4.61Z" fill="currentColor" />
        </svg>
      );
    default:
      return null;
  }
}

const socialNames: Record<SocialKey, string> = {
  facebook: "Facebook",
  twitter: "Twitter",
  instagram: "Instagram",
  linkedin: "LinkedIn",
};

function previewObject(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function previewColor(value: unknown, fallback: string): string {
  const normalized = typeof value === "string" ? value.trim() : "";
  return /^#[0-9a-f]{6}$/i.test(normalized) ? normalized : fallback;
}

function previewText(value: unknown, fallback: string): string {
  const normalized = typeof value === "string" ? value.trim() : "";
  return normalized || fallback;
}

function previewHref(value: unknown): string {
  const normalized = typeof value === "string" ? value.trim() : "";
  return /^\/(?!\/)/.test(normalized) || /^https?:\/\//i.test(normalized)
    ? normalized
    : "";
}

function previewLinkList(value: unknown): Array<{ href: string; label: string }> {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => ({
      href: previewHref(item["href"]),
      label: typeof item["label"] === "string" ? item["label"].trim() : "",
    }))
    .filter((item) => item.href && item.label);
}

function previewPaymentList(
  value: unknown,
): Array<{ label: string; href?: string; iconUrl?: string }> {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => ({
      label: typeof item["label"] === "string" ? item["label"].trim() : "",
      href: previewHref(item["href"]) || undefined,
      iconUrl: storefrontImageUrl(
        typeof item["icon_url"] === "string" ? item["icon_url"].trim() : "",
      ),
    }))
    .filter((item) => item.label || item.iconUrl);
}

type FooterProps = {
  initialStorefront?: PublicStorefront | null;
};

const Footer = ({ initialStorefront }: FooterProps) => {
  const initialBranding = initialStorefront ? getStorefrontBranding(initialStorefront) : null;
  const year = new Date().getFullYear();
  const [supportPhone, setSupportPhone] = useState(initialBranding?.supportPhone || "");
  const [supportEmail, setSupportEmail] = useState(initialBranding?.supportEmail || "");
  const [supportAddress, setSupportAddress] = useState(initialBranding?.supportAddress || "");
  const [footerText, setFooterText] = useState(initialBranding?.footerText || "Todos los derechos reservados.");
  const [footerBackgroundColor, setFooterBackgroundColor] = useState(initialBranding?.footer.backgroundColor || "#FFFFFF");
  const [footerTextColor, setFooterTextColor] = useState(initialBranding?.footer.textColor || "#1C274C");
  const [footerBottomBackgroundColor, setFooterBottomBackgroundColor] = useState(initialBranding?.footer.bottomBackgroundColor || "#F3F4F6");
  const [socialLinks, setSocialLinks] = useState<Array<{ key: string; href: string }>>(initialBranding?.socialLinks || []);
  const [helpTitle, setHelpTitle] = useState(initialBranding?.footer.helpTitle || "Ayuda y contacto");
  const [accountTitle, setAccountTitle] = useState(initialBranding?.footer.accountTitle || "Cuenta");
  const [quickLinksTitle, setQuickLinksTitle] = useState(initialBranding?.footer.quickLinksTitle || "Enlaces");
  const [appTitle, setAppTitle] = useState(initialBranding?.footer.appTitle || "App móvil");
  const [appDescription, setAppDescription] = useState(initialBranding?.footer.appDescription || "Compra desde cualquier lugar");
  const [appStoreSubtitle, setAppStoreSubtitle] = useState(initialBranding?.footer.appStoreSubtitle || "Disponible en");
  const [appStoreLabel, setAppStoreLabel] = useState(initialBranding?.footer.appStoreLabel || "App Store");
  const [appStoreUrl, setAppStoreUrl] = useState<string | undefined>(initialBranding?.footer.appStoreUrl);
  const [playStoreSubtitle, setPlayStoreSubtitle] = useState(initialBranding?.footer.playStoreSubtitle || "Disponible en");
  const [playStoreLabel, setPlayStoreLabel] = useState(initialBranding?.footer.playStoreLabel || "Google Play");
  const [playStoreUrl, setPlayStoreUrl] = useState<string | undefined>(initialBranding?.footer.playStoreUrl);
  const [paymentTitle, setPaymentTitle] = useState(initialBranding?.footer.paymentTitle || "Medios de pago:");
  const [showSocialLinks, setShowSocialLinks] = useState(initialBranding?.footer.showSocialLinks || false);
  const [showAppDownloads, setShowAppDownloads] = useState(initialBranding?.footer.showAppDownloads || false);
  const [showPaymentMethods, setShowPaymentMethods] = useState(initialBranding?.footer.showPaymentMethods || false);
  const [accountLinks, setAccountLinks] = useState<Array<{ href: string; label: string }>>(initialBranding?.footer.accountLinks || []);
  const [quickLinks, setQuickLinks] = useState<Array<{ href: string; label: string }>>(initialBranding?.footer.quickLinks || []);
  const [paymentMethods, setPaymentMethods] = useState<
    Array<{ label: string; href?: string; iconUrl?: string }>
  >(initialBranding?.footer.paymentMethods || []);
  const [previewMode, setPreviewMode] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedPreviewArea, setSelectedPreviewArea] = useState("");
  const previewDocumentApplied = useRef(false);

  useEffect(() => {
    let active = true;

    async function loadBranding() {
      try {
        const storefront = await resolveStorefront();
        const branding = getStorefrontBranding(storefront);

        if (!active || previewDocumentApplied.current) {
          return;
        }

        setSupportPhone(branding.supportPhone);
        setSupportEmail(branding.supportEmail);
        setSupportAddress(branding.supportAddress);
        setFooterText(branding.footerText);
        setFooterBackgroundColor(branding.footer.backgroundColor);
        setFooterTextColor(branding.footer.textColor);
        setFooterBottomBackgroundColor(branding.footer.bottomBackgroundColor);
        setSocialLinks(branding.socialLinks);
        setHelpTitle(branding.footer.helpTitle);
        setAccountTitle(branding.footer.accountTitle);
        setQuickLinksTitle(branding.footer.quickLinksTitle);
        setAppTitle(branding.footer.appTitle);
        setAppDescription(branding.footer.appDescription);
        setAppStoreSubtitle(branding.footer.appStoreSubtitle);
        setAppStoreLabel(branding.footer.appStoreLabel);
        setAppStoreUrl(branding.footer.appStoreUrl);
        setPlayStoreSubtitle(branding.footer.playStoreSubtitle);
        setPlayStoreLabel(branding.footer.playStoreLabel);
        setPlayStoreUrl(branding.footer.playStoreUrl);
        setPaymentTitle(branding.footer.paymentTitle);
        setShowSocialLinks(branding.footer.showSocialLinks);
        setShowAppDownloads(branding.footer.showAppDownloads);
        setShowPaymentMethods(branding.footer.showPaymentMethods);
        setAccountLinks(branding.footer.accountLinks);
        setQuickLinks(branding.footer.quickLinks);
        setPaymentMethods(branding.footer.paymentMethods);
      } catch {
        // keep template defaults when storefront branding is unavailable
      }
    }

    loadBranding();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setPreviewMode(window.parent !== window);
    const handlePreviewMessage = (event: MessageEvent) => {
      if (!isTrustedPreviewMessage(event)) return;
      const message = event.data;
      if (!message || message.type !== "lumefy:preview:apply" || message.template !== "home") return;

      const document = previewObject(message.document);
      const settings = previewObject(document["settings"]);
      const globalSettings = previewObject(settings["global"]);
      const footer = {
        ...previewObject(globalSettings["footer"]),
        ...previewObject(settings["footer"]),
      };
      previewDocumentApplied.current = true;
      setPreviewMode(true);

      if (typeof message.selectionMode === "boolean") {
        setSelectionMode(message.selectionMode);
      }
      if ("selectedGlobalArea" in message) {
        setSelectedPreviewArea(
          message.selectedGlobalArea === "header" || message.selectedGlobalArea === "footer"
            ? message.selectedGlobalArea
            : "",
        );
      }

      if (typeof footer["footer_text"] === "string") {
        const nextFooterText = footer["footer_text"].trim();
        setFooterText(nextFooterText.slice(0, 240));
      }
      if ("help_title" in footer) {
        setHelpTitle(previewText(footer["help_title"], "Ayuda y contacto"));
      }
      if ("account_title" in footer) {
        setAccountTitle(previewText(footer["account_title"], "Cuenta"));
      }
      if ("quick_links_title" in footer) {
        setQuickLinksTitle(previewText(footer["quick_links_title"], "Enlaces"));
      }
      if ("payment_title" in footer) {
        setPaymentTitle(previewText(footer["payment_title"], "Medios de pago:"));
      }
      if ("app_title" in footer) {
        setAppTitle(previewText(footer["app_title"], "App móvil"));
      }
      if ("app_description" in footer) {
        setAppDescription(previewText(footer["app_description"], "Compra desde cualquier lugar"));
      }
      if ("app_store_subtitle" in footer) {
        setAppStoreSubtitle(previewText(footer["app_store_subtitle"], "Disponible en"));
      }
      if ("app_store_label" in footer) {
        setAppStoreLabel(previewText(footer["app_store_label"], "App Store"));
      }
      if ("app_store_url" in footer) {
        setAppStoreUrl(previewHref(footer["app_store_url"]) || undefined);
      }
      if ("play_store_subtitle" in footer) {
        setPlayStoreSubtitle(previewText(footer["play_store_subtitle"], "Disponible en"));
      }
      if ("play_store_label" in footer) {
        setPlayStoreLabel(previewText(footer["play_store_label"], "Google Play"));
      }
      if ("play_store_url" in footer) {
        setPlayStoreUrl(previewHref(footer["play_store_url"]) || undefined);
      }
      if (typeof footer["support_phone"] === "string") {
        setSupportPhone(footer["support_phone"].trim().slice(0, 80));
      }
      if (typeof footer["support_email"] === "string") {
        setSupportEmail(footer["support_email"].trim().slice(0, 160));
      }
      if (typeof footer["support_address"] === "string") {
        setSupportAddress(footer["support_address"].trim().slice(0, 180));
      }
      if ("show_social_links" in footer && typeof footer["show_social_links"] === "boolean") {
        setShowSocialLinks(footer["show_social_links"] === true);
      }
      if ("show_app_downloads" in footer && typeof footer["show_app_downloads"] === "boolean") {
        setShowAppDownloads(footer["show_app_downloads"] === true);
      }
      if ("show_payment_methods" in footer && typeof footer["show_payment_methods"] === "boolean") {
        setShowPaymentMethods(footer["show_payment_methods"] === true);
      }
      if ("account_links" in footer) {
        setAccountLinks(previewLinkList(footer["account_links"]));
      }
      if ("quick_links" in footer) {
        setQuickLinks(previewLinkList(footer["quick_links"]));
      }
      if ("payment_methods" in footer) {
        setPaymentMethods(previewPaymentList(footer["payment_methods"]));
      }
      if ("social_links" in footer) {
        const social = previewObject(footer["social_links"]);
        setSocialLinks(
          (["facebook", "twitter", "instagram", "linkedin"] as const)
            .map((key) => {
              const value = social[key];
              return typeof value === "string" && value.trim()
                ? { key, href: value.trim() }
                : null;
            })
            .filter(
              (item): item is {
                key: "facebook" | "twitter" | "instagram" | "linkedin";
                href: string;
              } => Boolean(item),
            ),
        );
      }
      if ("background_color" in footer) {
        setFooterBackgroundColor(previewColor(footer["background_color"], "#FFFFFF"));
      }
      if ("text_color" in footer) {
        setFooterTextColor(previewColor(footer["text_color"], "#1C274C"));
      }
      if ("bottom_background_color" in footer) {
        setFooterBottomBackgroundColor(previewColor(footer["bottom_background_color"], "#F3F4F6"));
      }
    };

    window.addEventListener("message", handlePreviewMessage);
    return () => window.removeEventListener("message", handlePreviewMessage);
  }, []);

  const selectPreviewArea = (event: React.MouseEvent<HTMLElement>, area: "header" | "footer") => {
    if (!previewMode || !selectionMode) return;
    event.preventDefault();
    event.stopPropagation();
    window.parent.postMessage(
      { type: "lumefy:preview:select", area },
      previewParentOrigin() || "*",
    );
  };

  return (
    <footer
      onClickCapture={(event) => selectPreviewArea(event, "footer")}
      className={`storefront-footer overflow-hidden ${previewMode && selectionMode ? "lumefy-preview-global--selectable" : ""} ${selectedPreviewArea === "footer" ? "lumefy-preview-global--selected" : ""}`}
      data-lumefy-preview-area="footer"
      style={{
        backgroundColor: footerBackgroundColor,
        color: footerTextColor,
        "--storefront-footer-text": footerTextColor,
      } as React.CSSProperties}
    >
      <div className="max-w-[1170px] mx-auto px-4 sm:px-8 xl:px-0">
        <div className="flex flex-wrap xl:flex-nowrap gap-10 xl:gap-19 xl:justify-between pt-17.5 xl:pt-22.5 pb-10 xl:pb-15">
          <div className="max-w-[330px] w-full">
            <h2 className="mb-7.5 text-custom-1 font-medium text-dark">
              {helpTitle}
            </h2>

            <ul className="flex flex-col gap-3">
              {supportAddress ? <li>{supportAddress}</li> : null}
              {supportPhone ? <li>
                <a href={`tel:${supportPhone}`} className="ease-out duration-200 hover:text-blue">
                  {supportPhone}
                </a>
              </li> : null}
              {supportEmail ? <li>
                <a
                  href={`mailto:${supportEmail}`}
                  className="ease-out duration-200 hover:text-blue"
                >
                  {supportEmail}
                </a>
              </li> : null}
            </ul>

            {showSocialLinks && socialLinks.length > 0 ? (
              <div className="flex items-center gap-4 mt-7.5">
                {socialLinks.map((social) => (
                  <a
                    key={social.key}
                    href={social.href}
                    aria-label={socialNames[social.key as SocialKey] || social.key}
                    className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-3 ease-out duration-200 hover:border-blue hover:text-blue"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <SocialIcon name={social.key} />
                  </a>
                ))}
              </div>
            ) : null}
          </div>

          <div className="w-full sm:w-auto">
            <h2 className="mb-7.5 text-custom-1 font-medium text-dark">
              {accountTitle}
            </h2>

            <ul className="flex flex-col gap-3.5">
              {accountLinks.map((item) => (
                <li key={item.label}>
                  <Link className="ease-out duration-200 hover:text-blue" href={item.href}>
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="w-full sm:w-auto">
            <h2 className="mb-7.5 text-custom-1 font-medium text-dark">
              {quickLinksTitle}
            </h2>

            <ul className="flex flex-col gap-3">
              {quickLinks.map((item) => (
                <li key={item.label}>
                  <Link className="ease-out duration-200 hover:text-blue" href={item.href}>
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {showAppDownloads && (appStoreUrl || playStoreUrl) ? (
            <div className="w-full sm:w-auto">
            <h2 className="mb-7.5 text-custom-1 font-medium text-dark lg:text-right">
              {appTitle}
            </h2>

            <p className="lg:text-right text-custom-sm mb-4">
              {appDescription}
            </p>

            <ul className="flex flex-col lg:items-end gap-3">
              {appStoreUrl ? <li>
                <a
                  className="inline-flex items-center gap-3 py-[9px] pl-4 pr-7.5 text-white rounded-md bg-dark ease-out duration-200 hover:bg-opacity-95"
                  href={appStoreUrl || "#"}
                >
                  <div>
                    <span className="block text-custom-xs">
                      {appStoreSubtitle}
                    </span>
                    <p className="font-medium">{appStoreLabel}</p>
                  </div>
                </a>
              </li> : null}

              {playStoreUrl ? <li>
                <a
                  className="inline-flex items-center gap-3 py-[9px] pl-4 pr-8.5 text-white rounded-md bg-blue ease-out duration-200 hover:bg-opacity-95"
                  href={playStoreUrl || "#"}
                >
                  <div>
                    <span className="block text-custom-xs">{playStoreSubtitle}</span>
                    <p className="font-medium">{playStoreLabel}</p>
                  </div>
                </a>
              </li> : null}
            </ul>
            </div>
          ) : null}
        </div>
      </div>

      <div
        className="py-5 xl:py-7.5 bg-gray-1"
        style={{ backgroundColor: footerBottomBackgroundColor }}
      >
        <div className="max-w-[1170px] mx-auto px-4 sm:px-8 xl:px-0">
          <div className="flex gap-5 flex-wrap items-center justify-between">
            <p className="text-dark font-medium">
              &copy; {year}. {footerText}
            </p>

            {showPaymentMethods && paymentMethods.length > 0 ? (
              <div className="flex flex-wrap items-center gap-4">
                <p className="font-medium">{paymentTitle}</p>

                <div className="flex flex-wrap items-center gap-6">
                  {paymentMethods.map((method) => {
                    const content = method.iconUrl ? (
                      // Gateway icons are tenant-configured remote URLs, which cannot use Next's fixed image allowlist.
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={method.iconUrl}
                        alt={method.label}
                        className="max-h-6 w-auto object-contain"
                      />
                    ) : (
                      <span className="text-sm font-medium text-dark">{method.label}</span>
                    );

                    return method.href ? (
                      <a
                        key={`${method.label}-${method.iconUrl || "text"}`}
                        href={method.href}
                        aria-label={`payment method ${method.label}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {content}
                      </a>
                    ) : (
                      <div key={`${method.label}-${method.iconUrl || "text"}`} aria-label={`payment method ${method.label}`}>
                        {content}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
