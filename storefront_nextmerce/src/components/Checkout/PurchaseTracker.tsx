"use client";

import { useEffect } from "react";

import { trackPendingStorefrontPurchase } from "@/lib/storefront-tracking";

export default function PurchaseTracker({
  orderCode,
  paymentStatus,
  total,
  currency,
}: {
  orderCode?: string;
  paymentStatus?: string;
  total?: string;
  currency?: string;
}) {
  useEffect(() => {
    trackPendingStorefrontPurchase(orderCode, paymentStatus, {
      currency,
      value: total ? Number(total) : undefined,
    });
  }, [currency, orderCode, paymentStatus, total]);

  return null;
}
