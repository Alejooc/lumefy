import { redirect } from "next/navigation";

const ShopWithSidebarPage = async ({
  searchParams,
}: {
  searchParams: Promise<{
    collection?: string;
    q?: string;
    type?: string;
    size?: string;
    color?: string;
    sort?: string;
    minPrice?: string;
    maxPrice?: string;
  }>;
}) => {
  const params = new URLSearchParams();
  const resolved = await searchParams;
  for (const [key, value] of Object.entries(resolved)) {
    if (value) params.set(key, value);
  }
  redirect(params.toString() ? `/products?${params.toString()}` : "/products");
};

export default ShopWithSidebarPage;
