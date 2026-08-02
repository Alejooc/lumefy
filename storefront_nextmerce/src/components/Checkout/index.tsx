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
  getPublicShippingConfig,
} from "@/lib/storefront-api";
import {
  CheckoutPreviewResponse,
  PaymentIntentResponse,
  PublicStorePaymentGateway,
  PublicShippingConfig,
} from "@/types/storefront";
import { removeAllItemsFromCart } from "@/redux/features/cart-slice";
import { useDispatch } from "react-redux";
import { AppDispatch } from "@/redux/store";
import { useStorefrontAuth } from "@/lib/storefront-auth";

type Props = {
  storefrontId: string;
  currency: string;
  checkoutSettings?: Record<string, unknown>;
};

type CheckoutSettings = {
  allow_guest_checkout: boolean;
  checkout_mode: string;
  enable_order_notes: boolean;
  require_phone: boolean;
  show_delivery_estimate: boolean;
  flat_shipping_rate: number;
  free_shipping_threshold: number;
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
  city_code: string;
  state_code: string;
  postal_code: string;
  phone: string;
  document_id: string;
  email: string;
  notes: string;
  payment_provider: string;
  shipping_method_id: string;
  shipping_destination_id: string;
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
  city_code: "",
  state_code: "",
  postal_code: "",
  phone: "",
  document_id: "",
  email: "",
  notes: "",
  payment_provider: "manual_transfer",
  shipping_method_id: "",
  shipping_destination_id: "",
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

function numberSetting(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function normalizeCheckoutSettings(settings: Record<string, unknown> | undefined): CheckoutSettings {
  return {
    allow_guest_checkout: settings?.allow_guest_checkout !== false,
    checkout_mode: typeof settings?.checkout_mode === "string" ? settings.checkout_mode : "guest",
    enable_order_notes: settings?.enable_order_notes !== false,
    require_phone: settings?.require_phone === true,
    show_delivery_estimate: settings?.show_delivery_estimate !== false,
    flat_shipping_rate: numberSetting(settings?.flat_shipping_rate),
    free_shipping_threshold: numberSetting(settings?.free_shipping_threshold),
  };
}

function shippingStateKey(countryCode?: string | null, stateCode?: string | null, stateName?: string | null): string {
  const normalize = (value?: string | null) =>
    String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim()
      .toLowerCase();
  return `${normalize(countryCode)}|${normalize(stateCode || stateName)}`;
}

function checkoutErrorMessage(error: unknown, fallback: string): string {
  const message = error instanceof Error ? error.message : "";
  if (/no hay una tarifa de envío disponible|no hay una tarifa de envio disponible/i.test(message)) {
    return "No tenemos cobertura de envío para ese destino y método. Selecciona otra ubicación o contacta a la tienda.";
  }
  if (/método de envío seleccionado no está disponible|metodo de envio seleccionado no esta disponible/i.test(message)) {
    return "El método de envío seleccionado ya no está disponible. Elige otra opción.";
  }
  return message || fallback;
}

const Checkout = ({ storefrontId, currency, checkoutSettings }: Props) => {
  const router = useRouter();
  const dispatch = useDispatch<AppDispatch>();
  const cartItems = useAppSelector((state) => state.cartReducer.items);
  const { session, loading: authLoading } = useStorefrontAuth();
  const settings = useMemo(
    () => normalizeCheckoutSettings(checkoutSettings),
    [checkoutSettings],
  );
  const requiresAccount =
    settings.checkout_mode === "required_account" || !settings.allow_guest_checkout;
  const authenticatedForStorefront = session?.storefrontId === storefrontId;

  const [form, setForm] = useState<CheckoutFormState>(initialForm);
  const [preview, setPreview] = useState<CheckoutPreviewResponse | null>(null);
  const [paymentOptions, setPaymentOptions] = useState<PublicStorePaymentGateway[]>([]);
  const [shippingConfig, setShippingConfig] = useState<PublicShippingConfig>({ destinations: [], methods: [] });
  const [error, setError] = useState("");
  const [couponInput, setCouponInput] = useState("");
  const [appliedCoupon, setAppliedCoupon] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);
  const idempotencyKeyRef = useRef<string>(createCheckoutIdempotencyKey());
  const previewRequestRef = useRef(0);

  const shippingStateOptions = useMemo(() => {
    const options = new Map<string, {
      key: string;
      country_code: string;
      state_code?: string | null;
      state_name: string;
      department_destination_id?: string;
    }>();
    shippingConfig.destinations.forEach((destination) => {
      const key = shippingStateKey(destination.country_code, destination.state_code, destination.state_name);
      const current = options.get(key);
      if (!current) {
        options.set(key, {
          key,
          country_code: destination.country_code,
          state_code: destination.state_code,
          state_name: destination.state_name,
          department_destination_id: destination.destination_type === "department" ? destination.id : undefined,
        });
      } else if (!current.department_destination_id && destination.destination_type === "department") {
        current.department_destination_id = destination.id;
      }
    });
    return Array.from(options.values()).sort((a, b) => a.state_name.localeCompare(b.state_name, "es"));
  }, [shippingConfig.destinations]);

  const selectedShippingStateKey = shippingStateKey(form.country, form.state_code, form.state);
  const hasSelectedShippingState = Boolean(form.state.trim() || form.state_code.trim());
  const shippingCityOptions = useMemo(
    () => shippingConfig.destinations
      .filter((destination) => destination.destination_type === "city")
      .filter((destination) => shippingStateKey(destination.country_code, destination.state_code, destination.state_name) === selectedShippingStateKey)
      .sort((a, b) => (a.city_name || a.city_code || "").localeCompare(b.city_name || b.city_code || "", "es")),
    [selectedShippingStateKey, shippingConfig.destinations],
  );

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

  const payloadSignature = JSON.stringify(payloadItems);
  const shippingSignature = JSON.stringify({
    address: {
      line1: form.address_line1,
      postal_code: form.postal_code,
      city: form.city,
      state: form.state,
      country: form.country,
      city_code: form.city_code,
      state_code: form.state_code,
    },
    payment_provider: form.payment_provider,
    shipping_method_id: form.shipping_method_id,
  });

  const noCoverage = /no tenemos cobertura|no hay una tarifa de envío|no hay una tarifa de envio/i.test(error);

  const canSubmit =
    payloadItems.length > 0 &&
    Boolean(form.first_name.trim()) &&
    Boolean(form.last_name.trim()) &&
    Boolean(form.email.trim()) &&
    Boolean(form.address_line1.trim()) &&
    Boolean(form.city.trim()) &&
    Boolean(form.state.trim()) &&
    paymentOptions.length > 0 &&
    (shippingConfig.methods.length === 0 || Boolean(form.shipping_method_id)) &&
    (shippingConfig.destinations.length === 0 || Boolean(form.shipping_destination_id)) &&
    !noCoverage &&
    (!requiresAccount || authenticatedForStorefront) &&
    (!settings.require_phone || Boolean(form.phone.trim())) &&
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

  useEffect(() => {
    let active = true;
    getPublicShippingConfig(storefrontId)
      .then((config) => {
        if (!active) return;
        setShippingConfig(config);
        setForm((current) => {
          const methodId = current.shipping_method_id && config.methods.some((item) => item.id === current.shipping_method_id)
            ? current.shipping_method_id
            : config.methods[0]?.id || "";
          const destinationId = current.shipping_destination_id && config.destinations.some((item) => item.id === current.shipping_destination_id)
            ? current.shipping_destination_id
            : "";
          const destination = config.destinations.find((item) => item.id === destinationId);
          return {
            ...current,
            shipping_method_id: methodId,
            shipping_destination_id: destinationId,
            country: destination?.country_code || current.country,
            state: destination?.state_name || current.state,
            state_code: destination?.state_code || current.state_code,
            city: destination?.city_name || current.city,
            city_code: destination?.city_code || current.city_code,
          };
        });
      })
      .catch(() => {
        if (active) setShippingConfig({ destinations: [], methods: [] });
      });

    return () => {
      active = false;
    };
  }, [storefrontId]);

  useEffect(() => {
    if (!authenticatedForStorefront || !session?.user) {
      return;
    }

    const nameParts = (session.user.full_name || "").trim().split(/\s+/).filter(Boolean);
    setForm((current) => ({
      ...current,
      first_name: current.first_name || nameParts[0] || "",
      last_name: current.last_name || nameParts.slice(1).join(" "),
      email: current.email || session.user.email,
    }));
  }, [authenticatedForStorefront, session]);

  async function refreshPreview(): Promise<CheckoutPreviewResponse | null> {
    const requestId = ++previewRequestRef.current;
    setError("");
    setPreviewLoading(true);

    try {
      const response = await checkoutPreview(storefrontId, {
        items: payloadItems,
        coupon_code: appliedCoupon,
        payment_provider: form.payment_provider,
        shipping_method_id: form.shipping_method_id || null,
        address: form.address_line1.trim().length >= 4
          ? {
              line1: form.address_line1,
              city: form.city || null,
              state: form.state || null,
              country: form.country || null,
              postal_code: form.postal_code || null,
              state_code: form.state_code || null,
              city_code: form.city_code || null,
            }
          : null,
      });
      if (requestId !== previewRequestRef.current) {
        return null;
      }
      setPreview(response);
      return response;
    } catch (err) {
      if (requestId === previewRequestRef.current) {
        setPreview(null);
        setError(
          checkoutErrorMessage(err, "No pudimos calcular el resumen de tu pedido."),
        );
      }
      return null;
    } finally {
      if (requestId === previewRequestRef.current) {
        setPreviewLoading(false);
      }
    }
  }

  function applyCoupon() {
    setError("");
    setAppliedCoupon(couponInput.trim().toUpperCase() || null);
  }

  function selectShippingState(stateKey: string) {
    const state = shippingStateOptions.find((option) => option.key === stateKey);
    const stateCities = shippingConfig.destinations.filter(
      (destination) => destination.destination_type === "city" && shippingStateKey(destination.country_code, destination.state_code, destination.state_name) === stateKey,
    );
    setForm((current) => ({
      ...current,
      shipping_destination_id: stateCities.length ? "" : state?.department_destination_id || "",
      country: state?.country_code || current.country,
      state: state?.state_name || "",
      state_code: state?.state_code || "",
      city: "",
      city_code: "",
    }));
  }

  function selectShippingCity(destinationId: string) {
    const destination = shippingConfig.destinations.find((item) => item.id === destinationId);
    setForm((current) => ({
      ...current,
      shipping_destination_id: destinationId,
      state: destination?.state_name || "",
      state_code: destination?.state_code || "",
      city: destination?.city_name || "",
      city_code: destination?.city_code || "",
      country: destination?.country_code || current.country,
    }));
  }

  useEffect(() => {
    if (payloadItems.length) {
      void refreshPreview();
    } else {
      setPreview(null);
    }
    // The signature keeps the preview synchronized with local cart changes.
    // Coupon changes are applied explicitly by the coupon controls.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storefrontId, payloadSignature, appliedCoupon, shippingSignature]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || submitLoading) {
      return;
    }

    setError("");
    setSubmitLoading(true);

    try {
      const latestPreview = await refreshPreview();
      if (!latestPreview) {
        return;
      }

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
          state_code: form.state_code || null,
          city_code: form.city_code || null,
        },
        notes: form.notes || null,
        payment_provider: form.payment_provider,
        coupon_code: appliedCoupon,
        shipping_method_id: form.shipping_method_id || null,
        idempotency_key: idempotencyKeyRef.current,
      }, authenticatedForStorefront ? session?.token : undefined);

      if (order.shipping_quote_required) {
        dispatch(removeAllItemsFromCart());
        const quoteParams = new URLSearchParams({
          order_code: order.order_code,
          status: order.status,
          total: String(order.total),
          currency: order.currency || currency,
          payment_provider: order.payment_provider,
          payment_status: order.payment_status,
        });
        router.push(`/checkout/success?${quoteParams.toString()}`);
        return;
      }

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
      setError(checkoutErrorMessage(err, "No pudimos completar tu pedido."));
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

                    {shippingConfig.destinations.length > 0 ? (
                      <div className="mb-5">
                        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                          <div>
                            <label htmlFor="shippingState" className="block mb-2.5">
                              Departamento <span className="text-red">*</span>
                            </label>
                            <select
                              id="shippingState"
                              value={hasSelectedShippingState ? selectedShippingStateKey : ""}
                              onChange={(event) => selectShippingState(event.target.value)}
                              className="rounded-md border border-gray-3 bg-gray-1 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                            >
                              <option value="">Selecciona tu departamento</option>
                              {shippingStateOptions.map((state) => (
                                <option key={state.key} value={state.key}>{state.state_name}</option>
                              ))}
                            </select>
                          </div>

                          {hasSelectedShippingState && shippingCityOptions.length > 0 ? (
                            <div>
                              <label htmlFor="shippingCity" className="block mb-2.5">
                                Ciudad <span className="text-red">*</span>
                              </label>
                              <select
                                id="shippingCity"
                                value={form.shipping_destination_id}
                                onChange={(event) => selectShippingCity(event.target.value)}
                                className="rounded-md border border-gray-3 bg-gray-1 w-full py-2.5 px-5 outline-none focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                              >
                                <option value="">Selecciona tu ciudad</option>
                                {shippingCityOptions.map((destination) => (
                                  <option key={destination.id} value={destination.id}>{destination.city_name || destination.city_code}</option>
                                ))}
                              </select>
                            </div>
                          ) : hasSelectedShippingState ? (
                            <div>
                              <label htmlFor="shippingCityManual" className="block mb-2.5">
                                Ciudad <span className="text-red">*</span>
                              </label>
                              <input
                                type="text"
                                id="shippingCityManual"
                                value={form.city}
                                onChange={(event) => setForm({ ...form, city: event.target.value, city_code: "" })}
                                placeholder="Escribe tu ciudad o municipio"
                                className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                              />
                            </div>
                          ) : null}
                        </div>
                        <p className="mt-2 text-xs text-dark-5">
                          {hasSelectedShippingState && shippingCityOptions.length > 0
                            ? "Selecciona los valores configurados por la tienda para calcular tu tarifa."
                            : "La tienda cubre este departamento; escribe tu ciudad para validar la tarifa."}
                        </p>
                      </div>
                    ) : (
                      <>
                        <div className="mb-5">
                          <label htmlFor="town" className="block mb-2.5">
                            Ciudad <span className="text-red">*</span>
                          </label>
                          <input
                            type="text"
                            id="town"
                            value={form.city}
                            onChange={(event) =>
                              setForm({ ...form, city: event.target.value, city_code: "", shipping_destination_id: "" })
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
                              setForm({ ...form, state: event.target.value, state_code: "", shipping_destination_id: "" })
                            }
                            className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                          />
                        </div>
                      </>
                    )}

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
                        Telefono {settings.require_phone ? <span className="text-red">*</span> : null}
                      </label>
                      <input
                        type="tel"
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

                {settings.enable_order_notes ? (
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
                ) : null}
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
                        <p className="text-dark">{preview?.shipping_method_name || "Envío"}</p>
                      </div>
                      <div>
                        <p className="text-dark text-right">
                          {preview
                            ? preview.shipping_requires_destination
                              ? "Selecciona destino"
                              : preview.shipping_quote_required
                                ? "Por cotizar"
                                : preview.shipping > 0
                                  ? moneyLabel(preview.currency, preview.shipping)
                                  : "Gratis"
                            : "Calculando..."}
                        </p>
                      </div>
                    </div>

                    {preview && preview.discount > 0 ? (
                      <div className="flex items-center justify-between py-5 border-b border-gray-3">
                        <div>
                          <p className="text-dark">Descuento</p>
                        </div>
                        <div>
                          <p className="text-green-700 text-right">
                            -{moneyLabel(preview.currency, preview.discount)}
                          </p>
                        </div>
                      </div>
                    ) : null}

                    {preview && preview.tax > 0 ? (
                      <div className="flex items-center justify-between py-5 border-b border-gray-3">
                        <div>
                          <p className="text-dark">Impuestos</p>
                        </div>
                        <div>
                          <p className="text-dark text-right">
                            {moneyLabel(preview.currency, preview.tax)}
                          </p>
                        </div>
                      </div>
                    ) : null}

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
                    <h3 className="font-medium text-xl text-dark">Envío</h3>
                  </div>
                  <div className="p-4 sm:p-8.5">
                    <div className="space-y-3">
                      {shippingConfig.methods.map((method) => (
                        <label
                          key={method.id}
                          className={`flex cursor-pointer items-start justify-between gap-4 rounded-md border p-4 ${form.shipping_method_id === method.id ? "border-blue bg-blue/5" : "border-gray-3 bg-gray-1"}`}
                        >
                          <span className="flex min-w-0 items-start gap-3">
                            <input
                              type="radio"
                              name="shipping_method"
                              value={method.id}
                              checked={form.shipping_method_id === method.id}
                              onChange={(event) => setForm({ ...form, shipping_method_id: event.target.value })}
                              className="mt-1"
                            />
                            <span>
                              <span className="block font-medium text-dark">{method.name}</span>
                              <span className="mt-1 block text-sm text-dark-5">
                                {method.description || (settings.show_delivery_estimate ? "Entrega según cobertura y tarifa configurada." : "Método disponible en checkout.")}
                              </span>
                            </span>
                          </span>
                          <span className="shrink-0 font-medium text-dark">
                            {preview && preview.shipping_method_id === method.id
                              ? preview.shipping_requires_destination
                                ? "Selecciona destino"
                                : preview.shipping_quote_required
                                  ? "Por cotizar"
                                  : preview.shipping > 0
                                    ? moneyLabel(preview.currency, preview.shipping)
                                    : "Gratis"
                              : "—"}
                          </span>
                        </label>
                      ))}
                    </div>
                    {preview?.shipping_requires_destination ? (
                      <p className="mt-3 text-xs text-amber-700">Selecciona tu destino para calcular el envío.</p>
                    ) : null}
                    {preview?.shipping_quote_required ? (
                      <p className="mt-3 text-xs text-amber-700">La tienda confirmará el valor del envío antes de procesar el pago.</p>
                    ) : null}
                  </div>
                </div>

                <div className="bg-white shadow-1 rounded-[10px] mt-7.5">
                  <div className="border-b border-gray-3 py-5 px-4 sm:px-8.5">
                    <h3 className="font-medium text-xl text-dark">Cupón de descuento</h3>
                  </div>
                  <div className="p-4 sm:p-8.5">
                    <div className="flex flex-col gap-3 sm:flex-row">
                      <label htmlFor="checkoutCoupon" className="sr-only">Código de cupón</label>
                      <input
                        type="text"
                        id="checkoutCoupon"
                        value={couponInput}
                        onChange={(event) => setCouponInput(event.target.value.toUpperCase())}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            applyCoupon();
                          }
                        }}
                        placeholder="Ingresa tu código"
                        autoComplete="off"
                        className="min-w-0 flex-1 rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                      />
                      <button
                        type="button"
                        onClick={applyCoupon}
                        disabled={previewLoading}
                        className="inline-flex min-h-[46px] shrink-0 items-center justify-center font-medium text-white bg-blue py-3 px-6 rounded-md ease-out duration-200 hover:bg-blue-dark disabled:opacity-60"
                      >
                        {appliedCoupon ? "Actualizar cupón" : "Aplicar cupón"}
                      </button>
                    </div>
                    {appliedCoupon && preview?.discount ? (
                      <p className="mt-3 text-sm text-green-700">
                        Cupón {appliedCoupon} aplicado correctamente.
                      </p>
                    ) : null}
                    {appliedCoupon && !previewLoading && preview && preview.discount === 0 ? (
                      <button
                        type="button"
                        onClick={() => {
                          setCouponInput("");
                          setAppliedCoupon(null);
                        }}
                        className="mt-3 text-sm text-blue hover:text-blue-dark"
                      >
                        Quitar cupón
                      </button>
                    ) : null}
                  </div>
                </div>

                <div className="bg-white shadow-1 rounded-[10px] mt-7.5">
                  <div className="border-b border-gray-3 py-5 px-4 sm:px-8.5">
                    <h3 className="font-medium text-xl text-dark">
                      Metodo de pago
                    </h3>
                  </div>

                  <div className="p-4 sm:p-8.5">
                    {paymentOptions.length ? (
                    <div className="flex flex-col gap-3">
                      {paymentOptions.map((option) => ({
                        id: option.provider,
                        label: option.display_name,
                      })).map((option) => (
                        <label
                          key={option.id}
                          htmlFor={option.id}
                          className="flex cursor-pointer select-none items-start gap-3"
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
                            className={`min-w-0 flex-1 rounded-md border-[0.5px] py-3.5 px-5 ease-out duration-200 hover:bg-gray-2 hover:border-transparent hover:shadow-none ${
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
                    ) : (
                      <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                        Esta tienda todavía no tiene métodos de pago habilitados. Puedes continuar cuando el administrador configure uno.
                      </div>
                    )}
                  </div>
                </div>

                {requiresAccount && !authLoading && !authenticatedForStorefront ? (
                  <div className="mt-7.5 rounded-md border border-blue/20 bg-blue/5 p-4 text-sm text-dark">
                    <p className="font-medium">Necesitas una cuenta para comprar</p>
                    <p className="mt-1 text-dark-5">Inicia sesión o regístrate para continuar con este checkout.</p>
                    <Link href="/login" className="mt-3 inline-flex font-medium text-blue hover:text-blue-dark">
                      Iniciar sesión
                    </Link>
                  </div>
                ) : null}

                <div className="mt-7.5 flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={() => void refreshPreview()}
                    disabled={previewLoading || submitLoading || !payloadItems.length}
                    className="w-full min-h-[48px] flex justify-center items-center font-medium text-dark bg-white border border-gray-3 py-3 px-6 rounded-md ease-out duration-200 hover:border-blue hover:text-blue disabled:opacity-60"
                  >
                    {previewLoading ? "Calculando..." : "Actualizar resumen"}
                  </button>

                  <button
                    type="submit"
                    disabled={!canSubmit || submitLoading || previewLoading || authLoading}
                    className="w-full min-h-[48px] flex justify-center items-center font-medium text-white bg-blue py-3 px-6 rounded-md ease-out duration-200 hover:bg-blue-dark disabled:opacity-60"
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
