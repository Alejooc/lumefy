import MailSuccess from "@/components/MailSuccess";
import { getPaymentStatus, resolveStorefront } from "@/lib/storefront-api";
import { buildStorefrontPageMetadata } from "@/lib/seo";

export async function generateMetadata() {
  return buildStorefrontPageMetadata({
    title: "Compra confirmada",
    description: "Revisa el estado final de tu pedido.",
    path: "/checkout/success",
    index: false,
  });
}

const CheckoutSuccessPage = async ({
  searchParams,
}: {
  searchParams: Promise<{
    order_code?: string;
    status?: string;
    total?: string;
    currency?: string;
    payment_provider?: string;
    payment_status?: string;
    payment_message?: string;
    id?: string;
  }>;
}) => {
  const params = await searchParams;
  let paymentStatus = params.payment_status;
  let paymentMessage = params.payment_message;
  let orderCode = params.order_code;

  if (params.id && (params.payment_provider || "").toLowerCase() === "wompi") {
    try {
      const storefront = await resolveStorefront();
      const status = await getPaymentStatus(storefront.id, {
        provider: "wompi",
        transaction_id: params.id,
      });
      paymentStatus = status.status || paymentStatus;
      paymentMessage = status.status_message || paymentMessage;
      orderCode = status.order_code || orderCode;
    } catch {
      paymentMessage = paymentMessage || "No pudimos verificar el estado del pago automaticamente.";
    }
  }

  return (
    <main>
      <MailSuccess
        orderCode={orderCode}
        status={params.status}
        total={params.total}
        currency={params.currency}
        paymentProvider={params.payment_provider}
        paymentStatus={paymentStatus}
        paymentMessage={paymentMessage}
      />
    </main>
  );
};

export default CheckoutSuccessPage;
