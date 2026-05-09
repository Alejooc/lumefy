import Signup from "@/components/Auth/Signup";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Crear cuenta",
    description: "Crea tu cuenta de cliente.",
    path: "/register",
    index: false,
  });
}

const RegisterPage = () => {
  return (
    <main>
      <Signup />
    </main>
  );
};

export default RegisterPage;
