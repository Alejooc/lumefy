import { redirect } from "next/navigation";

const LegacyResetPasswordPage = async ({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) => {
  const params = new URLSearchParams();
  const resolved = await searchParams;

  Object.entries(resolved).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => params.append(key, item));
      return;
    }
    if (value) {
      params.set(key, value);
    }
  });

  redirect(params.size ? `/password/reset?${params.toString()}` : "/password/reset");
};

export default LegacyResetPasswordPage;
