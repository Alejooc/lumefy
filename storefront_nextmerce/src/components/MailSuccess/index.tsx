import React from "react";
import Breadcrumb from "../Common/Breadcrumb";
import Link from "next/link";

const MailSuccess = ({
  orderCode,
  status,
  total,
  currency,
  paymentProvider,
  paymentStatus,
  paymentMessage,
}: {
  orderCode?: string;
  status?: string;
  total?: string;
  currency?: string;
  paymentProvider?: string;
  paymentStatus?: string;
  paymentMessage?: string;
}) => {
  const normalizedPaymentStatus = (paymentStatus || "pending").toLowerCase();
  const isApproved = ["approved", "approved_partial", "paid"].includes(normalizedPaymentStatus);
  const isFailed = [
    "declined",
    "rejected",
    "cancelled",
    "expired",
    "error",
    "voided",
  ].includes(normalizedPaymentStatus);
  const heading = isApproved
    ? "Pago aprobado"
    : isFailed
      ? "Pago no completado"
      : "Pedido recibido";
  const eyebrow = isApproved ? "Listo" : isFailed ? "Revisa el pago" : "En confirmación";
  const description = isApproved
    ? "Tu pago fue aprobado. Prepararemos el pedido y te avisaremos cuando avance."
    : isFailed
      ? "No pudimos confirmar el pago. Puedes volver al carrito y elegir otro método de pago."
      : "Registramos tu pedido. Estamos esperando la confirmación del método de pago seleccionado.";
  return (
    <>
      <Breadcrumb title={"Pedido confirmado"} pages={["Pedido confirmado"]} />
      <section className="overflow-hidden py-20 bg-gray-2">
        <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
          <div className="bg-white rounded-xl shadow-1 px-4 py-10 sm:py-15 lg:py-20 xl:py-25">
            <div className="text-center">
              <h2 className="font-bold text-blue text-4xl lg:text-[45px] lg:leading-[57px] mb-5">
                {eyebrow}
              </h2>

              <h3 className="font-medium text-dark text-xl sm:text-2xl mb-3">
                {heading}
              </h3>

              <p className="max-w-[491px] w-full mx-auto mb-7.5">
                {description}
              </p>

              {orderCode || paymentMessage ? (
                <div className="mx-auto mb-7.5 max-w-[560px] rounded-xl border border-gray-3 bg-gray-1 p-6 text-left">
                  {orderCode ? (
                    <p className="mb-2 text-dark">
                      <span className="font-medium">Pedido:</span> {orderCode}
                    </p>
                  ) : null}
                  {status ? (
                    <p className="mb-2 text-dark">
                      <span className="font-medium">Estado:</span> {status}
                    </p>
                  ) : null}
                  {total && currency ? (
                    <p className="mb-2 text-dark">
                      <span className="font-medium">Total:</span> {total} {currency}
                    </p>
                  ) : null}
                  {paymentProvider ? (
                    <p className="mb-2 text-dark">
                      <span className="font-medium">Pago:</span> {paymentProvider}
                    </p>
                  ) : null}
                  {paymentStatus ? (
                    <p className="mb-2 text-dark">
                      <span className="font-medium">Estado del pago:</span> {paymentStatus}
                    </p>
                  ) : null}
                  {paymentMessage ? (
                    <p className="text-dark">
                      <span className="font-medium">Instrucciones:</span> {paymentMessage}
                    </p>
                  ) : null}
                </div>
              ) : null}

              <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Link
                  href={isFailed ? "/cart" : "/"}
                  className="inline-flex items-center justify-center gap-2 font-medium text-white bg-blue py-3 px-6 rounded-md ease-out duration-200 hover:bg-blue-dark"
                >
                  {isFailed ? "Volver al carrito" : "Volver al inicio"}
                </Link>
                {orderCode ? (
                  <Link
                    href="/account"
                    className="inline-flex items-center justify-center font-medium text-dark border border-gray-3 py-3 px-6 rounded-md ease-out duration-200 hover:border-blue hover:text-blue"
                  >
                    Ver mis pedidos
                  </Link>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
};

export default MailSuccess;
