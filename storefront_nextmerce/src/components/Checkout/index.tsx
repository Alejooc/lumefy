"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Breadcrumb from "../Common/Breadcrumb";
import { useAppSelector } from "@/redux/store";
import {
  checkoutPreview,
  createCheckoutOrder,
  createPaymentIntent,
  getPublicPaymentGateways,
} from "@/lib/storefront-api";
import {
  CheckoutPreviewResponse,
  PaymentIntentResponse,
  PublicStorePaymentGateway,
} from "@/types/storefront";
import { removeAllItemsFromCart } from "@/redux/features/cart-slice";
import { useDispatch } from "react-redux";
import { AppDispatch } from "@/redux/store";

type Props = {
  storefrontId: string;
  currency: string;
};

type CheckoutFormState = {
  first_name: string;
  last_name: string;
  company_name: string;
  country: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  postal_code: string;
  phone: string;
  document_id: string;
  email: string;
  notes: string;
  payment_provider: string;
};

const initialForm: CheckoutFormState = {
  first_name: "",
  last_name: "",
  company_name: "",
  country: "CO",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  postal_code: "",
  phone: "",
  document_id: "",
  email: "",
  notes: "",
  payment_provider: "manual_transfer",
};

function submitPaymentRedirect(intent: PaymentIntentResponse): boolean {
  const payload = intent.provider_payload || {};
  const action =
    typeof payload["action"] === "string"
      ? payload["action"]
      : intent.checkout_url || "";
  if (!action || typeof window === "undefined") {
    return false;
  }

  const method =
    typeof payload["method"] === "string"
      ? String(payload["method"]).toUpperCase()
      : "GET";
  const fields =
    payload["fields"] && typeof payload["fields"] === "object"
      ? (payload["fields"] as Record<string, unknown>)
      : {};

  const form = document.createElement("form");
  form.method = method;
  form.action = action;
  form.style.display = "none";

  for (const [key, value] of Object.entries(fields)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = key;
    input.value = String(value);
    form.appendChild(input);
  }

  document.body.appendChild(form);
  form.submit();
  return true;
}

function createCheckoutIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `checkout-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function moneyLabel(currency: string, value: number): string {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency,
  }).format(value);
}

const Checkout = ({ storefrontId, currency }: Props) => {
  const router = useRouter();
  const dispatch = useDispatch<AppDispatch>();
  const cartItems = useAppSelector((state) => state.cartReducer.items);

  const [form, setForm] = useState<CheckoutFormState>(initialForm);
  const [preview, setPreview] = useState<CheckoutPreviewResponse | null>(null);
  const [paymentOptions, setPaymentOptions] = useState<PublicStorePaymentGateway[]>([]);
  const [error, setError] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);
  const idempotencyKeyRef = useRef<string>(createCheckoutIdempotencyKey());

  const payloadItems = useMemo(
    () =>
      cartItems
        .filter((item) => item.publishedProductId)
        .map((item) => ({
          published_product_id: item.publishedProductId as string,
          quantity: item.quantity,
        })),
    [cartItems],
  );

  const estimatedSubtotal = useMemo(
    () =>
      cartItems.reduce(
        (total, item) => total + item.discountedPrice * item.quantity,
        0,
      ),
    [cartItems],
  );

  const canSubmit =
    payloadItems.length > 0 &&
    Boolean(form.first_name.trim()) &&
    Boolean(form.last_name.trim()) &&
    Boolean(form.email.trim()) &&
    Boolean(form.address_line1.trim()) &&
    Boolean(form.city.trim()) &&
    Boolean(form.state.trim()) &&
    (form.payment_provider !== "addi" || (Boolean(form.phone.trim()) && Boolean(form.document_id.trim())));

  useEffect(() => {
    let active = true;
    getPublicPaymentGateways(storefrontId)
      .then((gateways) => {
        if (!active) {
          return;
        }
        const sorted = gateways.slice().sort((a, b) => a.sort_order - b.sort_order);
        setPaymentOptions(sorted);
        setForm((current) => {
          if (!sorted.length || sorted.some((item) => item.provider === current.payment_provider)) {
            return current;
          }
          return { ...current, payment_provider: sorted[0].provider };
        });
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setPaymentOptions([]);
      });

    return () => {
      active = false;
    };
  }, [storefrontId]);

  async function handlePreview() {
    setError("");
    setPreviewLoading(true);

    try {
      const response = await checkoutPreview(storefrontId, {
        items: payloadItems,
      });
      setPreview(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No pudimos calcular el resumen de tu pedido.",
      );
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || submitLoading) {
      return;
    }

    setError("");
    setSubmitLoading(true);

    try {
      const order = await createCheckoutOrder(storefrontId, {
        items: payloadItems,
        customer: {
          full_name: `${form.first_name} ${form.last_name}`.replace(/\s+/g, " ").trim(),
          email: form.email,
          phone: form.phone || null,
          document_id: form.document_id || null,
        },
        address: {
          line1: form.address_line2
            ? `${form.address_line1}, ${form.address_line2}`
            : form.address_line1,
          city: form.city || null,
          state: form.state || null,
          country: form.country || null,
          postal_code: form.postal_code || null,
        },
        notes: form.notes || null,
        payment_provider: form.payment_provider,
        idempotency_key: idempotencyKeyRef.current,
      });

      const paymentIntent = await createPaymentIntent(storefrontId, {
        provider: form.payment_provider,
        amount: order.total,
        currency: order.currency || currency,
        order_id: order.order_id,
        customer_email: form.email,
        customer_full_name: `${form.first_name} ${form.last_name}`.replace(/\s+/g, " ").trim(),
        customer_phone: form.phone || null,
        shipping_address: {
          line1: form.address_line1,
          city: form.city,
          state: form.state,
          country: form.country,
          postal_code: form.postal_code,
          phone: form.phone,
        },
        return_url: `${
          typeof window !== "undefined" ? window.location.origin : ""
        }/checkout/success?order_code=${encodeURIComponent(order.order_code)}&status=${encodeURIComponent(order.status)}&total=${encodeURIComponent(String(order.total))}&currency=${encodeURIComponent(order.currency || currency)}&payment_provider=${encodeURIComponent(order.payment_provider)}&payment_status=${encodeURIComponent(order.payment_status)}`,
      });

      dispatch(removeAllItemsFromCart());
      idempotencyKeyRef.current = createCheckoutIdempotencyKey();

      if (paymentIntent.flow !== "manual" && submitPaymentRedirect(paymentIntent)) {
        return;
      }

      const params = new URLSearchParams({
        order_code: order.order_code,
        status: order.status,
        total: String(order.total),
        currency: order.currency || currency,
        payment_provider: order.payment_provider,
        payment_status: order.payment_status,
        payment_message: paymentIntent.checkout_url
          ? `Tu enlace de pago esta listo: ${paymentIntent.checkout_url}`
          : paymentIntent.instructions ||
            "Tu pedido fue creado y confirmaremos el pago por correo.",
      });

      router.push(`/checkout/success?${params.toString()}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No pudimos completar tu pedido.",
      );
    } finally {
      setSubmitLoading(false);
    }
  }

  if (!cartItems.length) {
    return (
      <>
        <Breadcrumb title="Pago" pages={["Pago"]} />
        <section className="overflow-hidden py-20 bg-gray-2">
          <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
            <div className="bg-white rounded-xl shadow-1 px-4 py-10 sm:py-15 lg:py-20 xl:py-25 text-center">
              <h2 className="font-medium text-dark text-2xl mb-3">
                Tu carrito esta vacio
              </h2>
              <p className="mb-7.5">Agrega productos antes de continuar con el pago.</p>
              <Link
                href="/products"
                className="inline-flex justify-center font-medium text-white bg-blue py-3 px-6 rounded-md ease-out duration-200 hover:bg-blue-dark"
              >
                Seguir comprando
              </Link>
            </div>
          </div>
        </section>
      </>
    );
  }

  return (
    <>
      <Breadcrumb title="Pago" pages={["Pago"]} />
      <section className="overflow-hidden py-20 bg-gray-2">
        <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
          {error ? (
            <div className="mb-7.5 rounded-md border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          <form onSubmit={handleSubmit}>
            <div className="flex flex-col lg:flex-row gap-7.5 xl:gap-11">
              <div className="lg:max-w-[670px] w-full">
                <div className="mt-0">
                  <h2 className="font-medium text-dark text-xl sm:text-2xl mb-5.5">
                    Datos de facturacion
                  </h2>

                  <div className="bg-white shadow-1 rounded-[10px] p-4 sm:p-8.5">
                    <div className="flex flex-col lg:flex-row gap-5 sm:gap-8 mb-5">
                      <div className="w-full">
                        <label htmlFor="firstName" className="block mb-2.5">
                          Nombre <span className="text-red">*</span>
                        </label>
                        <input
                          type="text"
                          id="firstName"
                          value={form.first_name}
                          onChange={(event) =>
                            setForm({ ...form, first_name: event.target.value })
                          }
                          placeholder="Tu nombre"
                          className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                        />
                      </div>

                      <div className="w-full">
                        <label htmlFor="lastName" className="block mb-2.5">
                          Apellido <span className="text-red">*</span>
                        </label>
                        <input
                          type="text"
                          id="lastName"
                          value={form.last_name}
                          onChange={(event) =>
                            setForm({ ...form, last_name: event.target.value })
                          }
                          placeholder="Tu apellido"
                          className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                        />
                      </div>
                    </div>

                    <div className="mb-5">
                      <label htmlFor="companyName" className="block mb-2.5">
                        Empresa
                      </label>
                      <input
                        type="text"
                        id="companyName"
                        value={form.company_name}
                        onChange={(event) =>
                          setForm({ ...form, company_name: event.target.value })
                        }
                        className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                      />
                    </div>

                    {form.payment_provider === "addi" ? (
                      <div className="mb-5">
                        <label htmlFor="documentId" className="block mb-2.5">
                          Cédula de ciudadanía <span className="text-red">*</span>
                        </label>
                        <input
                          type="text"
                          inputMode="numeric"
                          id="documentId"
                          value={form.document_id}
                          onChange={(event) =>
                            setForm({ ...form, document_id: event.target.value.replace(/\D/g, "") })
                          }
                          placeholder="Número de cédula"
                          className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                        />
                        <p className="mt-2 text-xs text-dark-5">Addi usa este dato únicamente para solicitar el crédito.</p>
                      </div>
                    ) : null}

                    <div className="mb-5">
                      <label htmlFor="countryName" className="block mb-2.5">
                        Pais / Region <span className="text-red">*</span>
                      </label>
                      <input
                        type="text"
                        id="countryName"
                        value={form.country}
                        onChange={(event) =>
                          setForm({ ...form, country: event.target.value })
                        }
                        className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                      />
                    </div>

                    <div className="mb-5">
                      <label htmlFor="address" className="block mb-2.5">
                        Direccion <span className="text-red">*</span>
                      </label>
                      <input
                        type="text"
                        id="address"
                        value={form.address_line1}
                        onChange={(event) =>
                          setForm({ ...form, address_line1: event.target.value })
                        }
                        placeholder="Calle, carrera, numero y barrio"
                        className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                      />

                      <div className="mt-5">
                        <input
                          type="text"
                          id="addressTwo"
                          value={form.address_line2}
                          onChange={(event) =>
                            setForm({ ...form, address_line2: event.target.value })
                          }
                          placeholder="Apartamento, torre, oficina u otra referencia"
                          className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                        />
                      </div>
                    </div>

                    <div className="mb-5">
                      <label htmlFor="town" className="block mb-2.5">
                        Ciudad <span className="text-red">*</span>
                      </label>
                      <input
                        type="text"
                        id="town"
                        value={form.city}
                        onChange={(event) =>
                          setForm({ ...form, city: event.target.value })
                        }
                        className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                      />
                    </div>

                    <div className="mb-5">
                      <label htmlFor="state" className="block mb-2.5">
                        Departamento / Provincia <span className="text-red">*</span>
                      </label>
                      <input
                        type="text"
                        id="state"
                        value={form.state}
                        onChange={(event) =>
                          setForm({ ...form, state: event.target.value })
                        }
                        className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                      />
                    </div>

                    <div className="mb-5">
                      <label htmlFor="postalCode" className="block mb-2.5">
                        Codigo postal
                      </label>
                      <input
                        type="text"
                        id="postalCode"
                        value={form.postal_code}
                        onChange={(event) =>
                          setForm({ ...form, postal_code: event.target.value })
                        }
                        className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                      />
                    </div>

                    <div className="mb-5">
                      <label htmlFor="phone" className="block mb-2.5">
                        Telefono <span className="text-red">*</span>
                      </label>
                      <input
                        type="text"
                        id="phone"
                        value={form.phone}
                        onChange={(event) =>
                          setForm({ ...form, phone: event.target.value })
                        }
                        className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                      />
                    </div>

                    <div className="mb-5.5">
                      <label htmlFor="email" className="block mb-2.5">
                        Correo electronico <span className="text-red">*</span>
                      </label>
                      <input
                        type="email"
                        id="email"
                        value={form.email}
                        onChange={(event) =>
                          setForm({ ...form, email: event.target.value })
                        }
                        className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                      />
                    </div>
                  </div>
                </div>

                <div className="bg-white shadow-1 rounded-[10px] p-4 sm:p-8.5 mt-7.5">
                  <div>
                    <label htmlFor="notes" className="block mb-2.5">
                      Notas del pedido
                    </label>

                    <textarea
                      id="notes"
                      rows={5}
                      value={form.notes}
                      onChange={(event) =>
                        setForm({ ...form, notes: event.target.value })
                      }
                      placeholder="Notas sobre tu pedido, por ejemplo indicaciones de entrega."
                      className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full p-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                    ></textarea>
                  </div>
                </div>
              </div>

              <div className="max-w-[455px] w-full">
                <div className="bg-white shadow-1 rounded-[10px]">
                  <div className="border-b border-gray-3 py-5 px-4 sm:px-8.5">
                    <h3 className="font-medium text-xl text-dark">
                      Tu pedido
                    </h3>
                  </div>

                  <div className="pt-2.5 pb-8.5 px-4 sm:px-8.5">
                    <div className="flex items-center justify-between py-5 border-b border-gray-3">
                      <div>
                        <h4 className="font-medium text-dark">Producto</h4>
                      </div>
                      <div>
                        <h4 className="font-medium text-dark text-right">
                          Subtotal
                        </h4>
                      </div>
                    </div>

                    {(preview?.items || []).length > 0
                      ? preview?.items.map((item) => (
                          <div
                            key={item.published_product_id}
                            className="flex items-center justify-between py-5 border-b border-gray-3"
                          >
                            <div>
                              <p className="text-dark">
                                {item.title} x {item.quantity}
                              </p>
                            </div>
                            <div>
                              <p className="text-dark text-right">
                                {moneyLabel(preview.currency, item.line_subtotal)}
                              </p>
                            </div>
                          </div>
                        ))
                      : cartItems.map((item) => (
                          <div
                            key={item.id}
                            className="flex items-center justify-between py-5 border-b border-gray-3"
                          >
                            <div>
                              <p className="text-dark">
                                {item.title} x {item.quantity}
                              </p>
                            </div>
                            <div>
                              <p className="text-dark text-right">
                                {moneyLabel(
                                  currency,
                                  item.discountedPrice * item.quantity,
                                )}
                              </p>
                            </div>
                          </div>
                        ))}

                    <div className="flex items-center justify-between py-5 border-b border-gray-3">
                      <div>
                        <p className="text-dark">Costo de envio</p>
                      </div>
                      <div>
                        <p className="text-dark text-right">
                          {preview
                            ? moneyLabel(preview.currency, preview.shipping)
                            : "Se calcula en el siguiente paso"}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-5">
                      <div>
                        <p className="font-medium text-lg text-dark">Total</p>
                      </div>
                      <div>
                        <p className="font-medium text-lg text-dark text-right">
                          {moneyLabel(
                            preview?.currency || currency,
                            preview?.total ?? estimatedSubtotal,
                          )}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white shadow-1 rounded-[10px] mt-7.5">
                  <div className="border-b border-gray-3 py-5 px-4 sm:px-8.5">
                    <h3 className="font-medium text-xl text-dark">
                      Metodo de pago
                    </h3>
                  </div>

                  <div className="p-4 sm:p-8.5">
                    <div className="flex flex-col gap-3">
                      {(paymentOptions.length
                        ? paymentOptions.map((option) => ({
                            id: option.provider,
                            label: option.display_name,
                          }))
                        : [
                            {
                              id: "manual_transfer",
                              label: "Transferencia bancaria",
                            },
                          ]).map((option) => (
                        <label
                          key={option.id}
                          htmlFor={option.id}
                          className="flex cursor-pointer select-none items-center gap-4"
                        >
                          <div className="relative">
                            <input
                              type="radio"
                              name="payment"
                              id={option.id}
                              checked={form.payment_provider === option.id}
                              onChange={() =>
                                setForm({ ...form, payment_provider: option.id })
                              }
                              className="sr-only"
                            />
                            <div
                              className={`flex h-4 w-4 items-center justify-center rounded-full ${
                                form.payment_provider === option.id
                                  ? "border-4 border-blue"
                                  : "border border-gray-4"
                              }`}
                            ></div>
                          </div>

                          <div
                            className={`rounded-md border-[0.5px] py-3.5 px-5 ease-out duration-200 hover:bg-gray-2 hover:border-transparent hover:shadow-none min-w-[240px] ${
                              form.payment_provider === option.id
                                ? "border-transparent bg-gray-2"
                                : " border-gray-4 shadow-1"
                            }`}
                          >
                            <p>{option.label}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-7.5 flex gap-4">
                  <button
                    type="button"
                    onClick={handlePreview}
                    disabled={previewLoading || submitLoading || !payloadItems.length}
                    className="w-full flex justify-center font-medium text-dark bg-white border border-gray-3 py-3 px-6 rounded-md ease-out duration-200 hover:border-blue hover:text-blue disabled:opacity-60"
                  >
                    {previewLoading ? "Calculando..." : "Actualizar resumen"}
                  </button>

                  <button
                    type="submit"
                    disabled={!canSubmit || submitLoading}
                    className="w-full flex justify-center font-medium text-white bg-blue py-3 px-6 rounded-md ease-out duration-200 hover:bg-blue-dark disabled:opacity-60"
                  >
                    {submitLoading ? "Procesando..." : "Finalizar compra"}
                  </button>
                </div>
              </div>
            </div>
          </form>
        </div>
      </section>
    </>
  );
};

export default Checkout;
