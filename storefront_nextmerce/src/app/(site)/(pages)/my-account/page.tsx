import { redirect } from "next/navigation";

const LegacyMyAccountPage = () => {
  redirect("/account");
};

export default LegacyMyAccountPage;
