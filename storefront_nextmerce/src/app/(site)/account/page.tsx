import MyAccount from "@/components/MyAccount";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Mi cuenta",
    description: "Administra tu cuenta de cliente.",
    path: "/account",
    index: false,
  });
}

const AccountPage = () => {
  return (
    <main>
      <MyAccount />
    </main>
  );
};

export default AccountPage;
