import React from "react";
import Cart from "@/components/Cart";
import { buildStorefrontPageMetadata } from "@/lib/seo";
import { resolveStorefront } from "@/lib/storefront-api";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Carrito",
    description: "Revisa los productos de tu carrito.",
    path: "/cart",
    index: false,
  });
}

const CartPage = async () => {
  const storefront = await resolveStorefront();

  return (
    <>
      <Cart cartTemplate={storefront.theme_documents?.cart || {}} />
    </>
  );
};

export default CartPage;
