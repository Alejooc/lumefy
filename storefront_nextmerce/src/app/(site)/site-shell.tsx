"use client";

import type { CSSProperties } from "react";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

import "../css/euclid-circular-a-font.css";
import "../css/style.css";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import { ModalProvider } from "../context/QuickViewModalContext";
import { CartModalProvider } from "../context/CartSidebarModalContext";
import { useCartModalContext } from "../context/CartSidebarModalContext";
import { useModalContext } from "../context/QuickViewModalContext";
import { usePreviewSlider } from "../context/PreviewSliderContext";
import { ReduxProvider } from "@/redux/provider";
import type { PublicStorefront } from "@/types/storefront";
import { StorefrontAuthProvider } from "@/lib/storefront-auth";
import { StorefrontCurrencyProvider } from "@/lib/storefront-currency";
import { PreviewSliderProvider } from "../context/PreviewSliderContext";
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
import { StorefrontUiProvider } from "@/lib/storefront-ui";
import type { JsonLdDocument } from "@/lib/structured-data";
import { serializeJsonLd } from "@/lib/structured-data";
import { StorefrontTrackingProvider } from "@/lib/storefront-tracking";
import type { PublicCollection, PublicStoreNavigationItem } from "@/types/storefront";

const QuickViewModal = dynamic(() => import("@/components/Common/QuickViewModal"), { ssr: false });
const CartSidebarModal = dynamic(() => import("@/components/Common/CartSidebarModal"), { ssr: false });
const PreviewSliderModal = dynamic(() => import("@/components/Common/PreviewSlider"), { ssr: false });

function DeferredQuickViewModal() {
  const { isModalOpen } = useModalContext();
  return isModalOpen ? <QuickViewModal /> : null;
}

function DeferredCartSidebarModal() {
  const { isCartModalOpen } = useCartModalContext();
  return isCartModalOpen ? <CartSidebarModal /> : null;
}

function DeferredPreviewSliderModal() {
  const { isModalPreviewOpen } = usePreviewSlider();
  return isModalPreviewOpen ? <PreviewSliderModal /> : null;
}

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
  initialNavigation,
  initialCollections,
  globalStructuredData,
}: {
  children: React.ReactNode;
  initialStorefront: PublicStorefront;
  initialNavigation: PublicStoreNavigationItem[];
  initialCollections: PublicCollection[];
  globalStructuredData?: JsonLdDocument;
}) {
  const [themeStyles, setThemeStyles] = useState(() => getStorefrontThemeStyles(initialStorefront));
  const [faviconUrl, setFaviconUrl] = useState(
    () => getStorefrontBranding(initialStorefront).faviconUrl || "",
  );

  useEffect(() => {
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
      window.removeEventListener("message", handlePreviewMessage);
    };
  }, [initialStorefront]);

  return (
    <html lang="es-CO" suppressHydrationWarning={true}>
      <head>
        {faviconUrl ? <link rel="icon" href={faviconUrl} data-storefront-favicon="true" /> : null}
      </head>
      <body className="storefront-theme overflow-x-hidden" style={themeStyleVariables(themeStyles)}>
        <StorefrontTrackingProvider storefrontId={initialStorefront.id} currency={initialStorefront.currency || "USD"}>
          <ReduxProvider>
            <StorefrontCurrencyProvider>
              <StorefrontAuthProvider>
                <CartModalProvider>
                  <ModalProvider>
                    <PreviewSliderProvider>
                      <StorefrontUiProvider initialStorefront={initialStorefront}>
                        <Header
                          initialStorefront={initialStorefront}
                          initialNavigation={initialNavigation}
                          initialCollections={initialCollections}
                        />
                        {children}
                        <CartFeedback />
                        <DeferredQuickViewModal />
                        <DeferredCartSidebarModal />
                        <DeferredPreviewSliderModal />
                      </StorefrontUiProvider>
                    </PreviewSliderProvider>
                  </ModalProvider>
                </CartModalProvider>
              </StorefrontAuthProvider>
            </StorefrontCurrencyProvider>
          </ReduxProvider>
        </StorefrontTrackingProvider>
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
