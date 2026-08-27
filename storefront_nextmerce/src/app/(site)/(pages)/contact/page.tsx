import InformativePage from "@/components/InformativePage";
import { resolveStorefront } from "@/lib/storefront-api";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Contacto",
    description: "Ponte en contacto con la tienda.",
    path: "/contact",
  });
}

export const dynamic = "force-dynamic";

const ContactPage = async () => {
  const storefront = await resolveStorefront();

  return (
    <main>
      <InformativePage pageSlug="contact" pageTemplate={storefront.theme_documents?.pages || {}} />
    </main>
  );
};

export default ContactPage;
