import React from "react";
import { Wishlist } from "@/components/Wishlist";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Favoritos",
    description: "Revisa los productos guardados.",
    path: "/wishlist",
    index: false,
  });
}

const WishlistPage = () => {
  return (
    <main>
      <Wishlist />
    </main>
  );
};

export default WishlistPage;
