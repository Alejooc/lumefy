import Signin from "@/components/Auth/Signin";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Ingresar",
    description: "Accede a tu cuenta de cliente.",
    path: "/login",
    index: false,
  });
}

const LoginPage = () => {
  return (
    <main>
      <Signin />
    </main>
  );
};

export default LoginPage;
