"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { resolveStorefront } from "./storefront-api";
import { formatMoney } from "./money";

type StorefrontCurrencyContextValue = {
  currency: string;
  showDecimals: boolean;
  format: (value: number | null | undefined) => string;
};

const StorefrontCurrencyContext = createContext<StorefrontCurrencyContextValue>({
  currency: "USD",
  showDecimals: false,
  format: (value) => formatMoney(value, "USD", false),
});

export function StorefrontCurrencyProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [currency, setCurrency] = useState("USD");
  const [showDecimals, setShowDecimals] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadCurrency() {
      try {
        const storefront = await resolveStorefront();
        if (active && storefront.currency) {
          setCurrency(storefront.currency);
          const themeSettings =
            storefront.theme_settings && typeof storefront.theme_settings === "object"
              ? (storefront.theme_settings as Record<string, unknown>)
              : {};
          const currencySettings =
            themeSettings["currency_settings"] &&
            typeof themeSettings["currency_settings"] === "object"
              ? (themeSettings["currency_settings"] as Record<string, unknown>)
              : {};
          setShowDecimals(currencySettings["show_decimals"] === true);
        }
      } catch {
        // Keep USD fallback when storefront config is unavailable.
      }
    }

    loadCurrency();

    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<StorefrontCurrencyContextValue>(
    () => ({
      currency,
      showDecimals,
      format: (amount) => formatMoney(amount, currency, showDecimals),
    }),
    [currency, showDecimals],
  );

  return (
    <StorefrontCurrencyContext.Provider value={value}>
      {children}
    </StorefrontCurrencyContext.Provider>
  );
}

export function useStorefrontCurrency() {
  return useContext(StorefrontCurrencyContext);
}
