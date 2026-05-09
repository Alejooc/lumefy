import Contact from "@/components/Contact";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Contacto",
    description: "Ponte en contacto con la tienda.",
    path: "/contact",
  });
}

const ContactPage = () => {
  return (
    <main>
      <Contact />
    </main>
  );
};

export default ContactPage;
