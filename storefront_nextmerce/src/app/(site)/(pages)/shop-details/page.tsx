import { redirect } from "next/navigation";

const ShopDetailsPage = async ({
  searchParams,
}: {
  searchParams: Promise<{ slug?: string }>;
}) => {
  const { slug } = await searchParams;
  redirect(slug ? `/products/${encodeURIComponent(slug)}` : "/products");
};

export default ShopDetailsPage;
