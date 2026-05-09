import ResetPassword from "@/components/Auth/ResetPassword";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Restablecer contrasena",
    description: "Recupera el acceso a tu cuenta.",
    path: "/password/reset",
    index: false,
  });
}

const PasswordResetPage = () => {
  return (
    <main>
      <ResetPassword />
    </main>
  );
};

export default PasswordResetPage;
