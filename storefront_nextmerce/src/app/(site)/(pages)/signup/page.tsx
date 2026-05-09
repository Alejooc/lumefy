import { redirect } from "next/navigation";

const LegacySignupPage = () => {
  redirect("/register");
};

export default LegacySignupPage;
