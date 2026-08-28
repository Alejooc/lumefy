"use client";

import type { CSSProperties } from "react";
import { useEffect, useState } from "react";

import "../css/euclid-circular-a-font.css";
import "../css/style.css";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import { ModalProvider } from "../context/QuickViewModalContext";
import { CartModalProvider } from "../context/CartSidebarModalContext";
import { ReduxProvider } from "@/redux/provider";
import type { PublicStorefront } from "@/types/storefront";
import { StorefrontAuthProvider } from "@/lib/storefront-auth";
import { StorefrontCurrencyProvider } from "@/lib/storefront-currency";
import QuickViewModal from "@/components/Common/QuickViewModal";
import CartSidebarModal from "@/components/Common/CartSidebarModal";
import { PreviewSliderProvider } from "../context/PreviewSliderContext";
import PreviewSliderModal from "@/components/Common/PreviewSlider";
import ScrollToTop from "@/components/Common/ScrollToTop";
import CartFeedback from "@/components/Common/CartFeedback";
import { isTrustedPreviewMessage } from "@/lib/preview";
import {
  getStorefrontBranding,
  getStorefrontThemeStyles,
  getThemeStylesFromDocumentSettings,
} from "@/lib/storefront-branding";
import type { StorefrontThemeStyleViewModel } from "@/lib/storefront-branding";
import { storefrontImageUrl } from "@/lib/storefront-image";
import { resolveStorefront } from "@/lib/storefront-api";
import { StorefrontUiProvider } from "@/lib/storefront-ui";
import type { JsonLdDocument } from "@/lib/structured-data";
import { serializeJsonLd } from "@/lib/structured-data";

function themeStyleVariables(styles: StorefrontThemeStyleViewModel): CSSProperties {
  return {
    "--storefront-primary": styles.primaryColor,
    "--storefront-accent": styles.accentColor,
    "--storefront-page-background": styles.pageBackgroundColor,
    "--storefront-body-text": styles.bodyTextColor,
    "--storefront-heading-text": styles.headingTextColor,
    "--storefront-body-font": styles.bodyFont,
    "--storefront-heading-font": styles.headingFont,
    "--storefront-content-width": `${styles.contentWidth}px`,
    "--storefront-corner-radius": styles.cornerRadius,
  } as CSSProperties;
}

export default function SiteShell({
  children,
  initialStorefront,
  globalStructuredData,
}: {
  children: React.ReactNode;
  initialStorefront: PublicStorefront;
  globalStructuredData?: JsonLdDocument;
}) {
  const [themeStyles, setThemeStyles] = useState(() => getStorefrontThemeStyles(initialStorefront));
  const [faviconUrl, setFaviconUrl] = useState(
    () => getStorefrontBranding(initialStorefront).faviconUrl || "",
  );

  useEffect(() => {
    let active = true;

    resolveStorefront()
      .then((storefront) => {
        if (!active) return;
        setThemeStyles(getStorefrontThemeStyles(storefront));
        setFaviconUrl(getStorefrontBranding(storefront).faviconUrl || "");
      })
      .catch(() => {
        // The server-provided storefront remains usable if the refresh fails.
      });

    const handlePreviewMessage = (event: MessageEvent) => {
      if (!isTrustedPreviewMessage(event)) return;
      const message = event.data;
      if (!message || message.type !== "lumefy:preview:apply" || !["home", "product", "collection", "search", "cart", "pages"].includes(message.template)) return;
      const document = message.document && typeof message.document === "object"
        ? message.document as Record<string, unknown>
        : {};
      const settings = document["settings"] && typeof document["settings"] === "object"
        ? document["settings"]
        : {};
      const globalSettings = settings && typeof settings === "object" && !Array.isArray(settings)
        && "global" in settings && typeof settings.global === "object" && settings.global !== null
        ? settings.global
        : {};
      const identity = {
        ...(globalSettings && typeof globalSettings === "object" && !Array.isArray(globalSettings)
          && "branding" in globalSettings && typeof globalSettings.branding === "object" && globalSettings.branding !== null
          ? globalSettings.branding
          : {}),
        ...(settings && typeof settings === "object" && !Array.isArray(settings)
          && "branding" in settings && typeof settings.branding === "object" && settings.branding !== null
          ? settings.branding
          : {}),
      } as Record<string, unknown>;
      // Product templates only change the product page. Keep the already
      // resolved storefront palette while previewing them so a document that
      // contains content settings cannot reset the global theme.
      if (message.template === "home") {
        setThemeStyles(getThemeStylesFromDocumentSettings(settings));
      }
      if ("favicon_url" in identity) {
        setFaviconUrl(
          storefrontImageUrl(typeof identity.favicon_url === "string" ? identity.favicon_url : "") || "",
        );
      }
    };

    window.addEventListener("message", handlePreviewMessage);
    return () => {
      active = false;
      window.removeEventListener("message", handlePreviewMessage);
    };
  }, [initialStorefront]);

  return (
    <html lang="es-CO" suppressHydrationWarning={true}>
      <head>
        {faviconUrl ? <link rel="icon" href={faviconUrl} data-storefront-favicon="true" /> : null}
      </head>
      <body className="storefront-theme overflow-x-hidden" style={themeStyleVariables(themeStyles)}>
        <ReduxProvider>
          <StorefrontCurrencyProvider>
            <StorefrontAuthProvider>
              <CartModalProvider>
                <ModalProvider>
                  <PreviewSliderProvider>
                    <StorefrontUiProvider initialStorefront={initialStorefront}>
                      <Header initialStorefront={initialStorefront} />
                      {children}
                      <CartFeedback />
                      <QuickViewModal />
                      <CartSidebarModal />
                      <PreviewSliderModal />
                    </StorefrontUiProvider>
                  </PreviewSliderProvider>
                </ModalProvider>
              </CartModalProvider>
            </StorefrontAuthProvider>
          </StorefrontCurrencyProvider>
        </ReduxProvider>
        {globalStructuredData ? (
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: serializeJsonLd(globalStructuredData) }}
          />
        ) : null}
        <ScrollToTop />
        <Footer initialStorefront={initialStorefront} />
      </body>
    </html>
  );
}
