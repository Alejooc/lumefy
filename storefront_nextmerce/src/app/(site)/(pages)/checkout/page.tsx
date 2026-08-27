import React from "react";
import Checkout from "@/components/Checkout";
import { resolveStorefront } from "@/lib/storefront-api";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Checkout",
    description: "Completa tu pedido de forma segura.",
    path: "/checkout",
    index: false,
  });
}

export const dynamic = "force-dynamic";

const CheckoutPage = async () => {
  const storefront = await resolveStorefront();

  return (
    <main>
      <Checkout
        storefrontId={storefront.id}
        currency={storefront.currency}
        checkoutSettings={storefront.checkout_settings}
        storefrontName={storefront.name}
        logoUrl={storefront.branding.logo_url}
      />
    </main>
  );
};

export default CheckoutPage;
