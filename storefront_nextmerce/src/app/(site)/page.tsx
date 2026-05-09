import Home from "@/components/Home";
import { loadHomeViewModel } from "@/lib/home-data";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "",
    description: "Compra online en nuestra tienda.",
    path: "/",
  });
}

export default async function HomePage() {
  const data = await loadHomeViewModel();
  return <Home data={data} />;
}
