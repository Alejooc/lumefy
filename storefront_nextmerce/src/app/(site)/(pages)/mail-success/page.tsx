import { redirect } from "next/navigation";

const LegacyMailSuccessPage = async ({
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

  redirect(params.size ? `/checkout/success?${params.toString()}` : "/checkout/success");
};

export default LegacyMailSuccessPage;
