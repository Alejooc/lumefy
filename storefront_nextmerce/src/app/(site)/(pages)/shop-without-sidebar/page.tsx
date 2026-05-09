import { redirect } from "next/navigation";

const ShopWithoutSidebarPage = async ({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; sort?: string; minPrice?: string; maxPrice?: string; type?: string; size?: string; color?: string }>;
}) => {
  const params = new URLSearchParams();
  const resolved = await searchParams;
  for (const [key, value] of Object.entries(resolved)) {
    if (value) params.set(key, value);
  }
  redirect(params.toString() ? `/products?${params.toString()}` : "/products");
};

export default ShopWithoutSidebarPage;
