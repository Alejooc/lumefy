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
import { StorefrontAuthProvider } from "@/lib/storefront-auth";
import { StorefrontCurrencyProvider } from "@/lib/storefront-currency";
import QuickViewModal from "@/components/Common/QuickViewModal";
import CartSidebarModal from "@/components/Common/CartSidebarModal";
import { PreviewSliderProvider } from "../context/PreviewSliderContext";
import PreviewSliderModal from "@/components/Common/PreviewSlider";
import ScrollToTop from "@/components/Common/ScrollToTop";
import PreLoader from "@/components/Common/PreLoader";
import CartFeedback from "@/components/Common/CartFeedback";
import { isTrustedPreviewMessage } from "@/lib/preview";
import {
  getStorefrontThemeStyles,
  getThemeStylesFromDocumentSettings,
} from "@/lib/storefront-branding";
import type { StorefrontThemeStyleViewModel } from "@/lib/storefront-branding";
import { resolveStorefront } from "@/lib/storefront-api";

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

export default function SiteShell({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [themeStyles, setThemeStyles] = useState(() => getStorefrontThemeStyles(null));

  useEffect(() => {
    const timeout = window.setTimeout(() => setLoading(false), 1000);
    return () => window.clearTimeout(timeout);
  }, []);

  useEffect(() => {
    let active = true;

    resolveStorefront()
      .then((storefront) => {
        if (active) setThemeStyles(getStorefrontThemeStyles(storefront));
      })
      .catch(() => {
        // Keep the built-in theme defaults when the public storefront is unavailable.
      });

    const handlePreviewMessage = (event: MessageEvent) => {
      if (!isTrustedPreviewMessage(event)) return;
      const message = event.data;
      if (!message || message.type !== "lumefy:preview:apply" || message.template !== "home") return;
      const document = message.document && typeof message.document === "object"
        ? message.document as Record<string, unknown>
        : {};
      const settings = document["settings"] && typeof document["settings"] === "object"
        ? document["settings"]
        : {};
      setThemeStyles(getThemeStylesFromDocumentSettings(settings));
    };

    window.addEventListener("message", handlePreviewMessage);
    return () => {
      active = false;
      window.removeEventListener("message", handlePreviewMessage);
    };
  }, []);

  return (
    <html lang="es-CO" suppressHydrationWarning={true}>
      <body className="storefront-theme overflow-x-hidden" style={themeStyleVariables(themeStyles)}>
        {loading ? (
          <PreLoader />
        ) : (
          <>
            <ReduxProvider>
              <StorefrontCurrencyProvider>
                <StorefrontAuthProvider>
                  <CartModalProvider>
                    <ModalProvider>
                      <PreviewSliderProvider>
                        <Header />
                        {children}
                        <CartFeedback />
                        <QuickViewModal />
                        <CartSidebarModal />
                        <PreviewSliderModal />
                      </PreviewSliderProvider>
                    </ModalProvider>
                  </CartModalProvider>
                </StorefrontAuthProvider>
              </StorefrontCurrencyProvider>
            </ReduxProvider>
            <ScrollToTop />
            <Footer />
          </>
        )}
      </body>
    </html>
  );
}
