import Home from "@/components/Home";
import { loadHomeViewModel } from "@/lib/home-data";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "",
    // Use the storefront-specific SEO settings, with a useful dynamic
    // fallback when the merchant has not configured a description yet.
    description: "",
    path: "/",
  });
}

export default async function HomePage() {
  const data = await loadHomeViewModel();
  return <Home data={data} />;
}
