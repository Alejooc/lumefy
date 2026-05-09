import React from "react";
import Cart from "@/components/Cart";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Carrito",
    description: "Revisa los productos de tu carrito.",
    path: "/cart",
    index: false,
  });
}

const CartPage = () => {
  return (
    <>
      <Cart />
    </>
  );
};

export default CartPage;
