import { redirect } from "next/navigation";

const LegacySigninPage = () => {
  redirect("/login");
};

export default LegacySigninPage;
