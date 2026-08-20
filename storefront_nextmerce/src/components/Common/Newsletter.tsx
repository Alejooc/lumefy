"use client";

import Image from "next/image";
import { FormEvent, useState } from "react";

import { HomeNewsletter } from "@/types/home";
import {
  StorefrontApiError,
  subscribeStorefrontNewsletter,
} from "@/lib/storefront-api";

const Newsletter = ({
  storefrontId,
  content,
}: {
  storefrontId: string;
  content: HomeNewsletter;
}) => {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!content.enabled) return null;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail) return;

    setSubmitting(true);
    setMessage(null);
    setError(null);
    try {
      const response = await subscribeStorefrontNewsletter(storefrontId, normalizedEmail);
      setMessage(response.msg);
      setEmail("");
    } catch (err) {
      setError(
        err instanceof StorefrontApiError && err.status !== 422
          ? err.message
          : "Revisa tu correo e inténtalo de nuevo.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="overflow-hidden bg-[#f4f0e9] py-8 sm:py-12">
      <div className="mx-auto w-full max-w-[1240px] px-4 sm:px-8 xl:px-0">
        <div className="relative isolate overflow-hidden rounded-[28px] bg-[#17233f] px-6 py-10 text-white sm:px-10 sm:py-12 lg:px-14 lg:py-14">
          <Image
            src={content.backgroundImageUrl || "/images/shapes/newsletter-bg.jpg"}
            alt=""
            fill
            sizes="(max-width: 1240px) 100vw, 1240px"
            className="-z-20 object-cover opacity-[0.13] mix-blend-luminosity"
          />
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_82%_10%,rgba(230,177,143,0.3),transparent_36%),linear-gradient(105deg,rgba(23,35,63,0.98)_35%,rgba(23,35,63,0.78))]" />
          <div className="absolute -bottom-20 -right-16 -z-10 h-60 w-60 rounded-full border-[42px] border-white/[0.05]" />

          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(380px,0.8fr)] lg:items-center lg:gap-14">
            <div className="max-w-[610px]">
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#e6b18f]">
                Ideas para disfrutar tu hogar
              </p>
              <h2 className="text-[30px] font-semibold leading-[1.08] tracking-[-0.025em] sm:text-[42px]">
                {content.title}
              </h2>
              {content.description ? (
                <p className="mt-4 max-w-[560px] text-sm leading-7 text-white/72 sm:text-base">
                  {content.description}
                </p>
              ) : null}
            </div>

            <div>
              <form onSubmit={handleSubmit} className="rounded-[20px] bg-white p-2 shadow-[0_18px_50px_rgba(0,0,0,0.18)] sm:flex">
                <label htmlFor="newsletter-email" className="sr-only">
                  Correo electrónico
                </label>
                <input
                  id="newsletter-email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder={content.placeholder || "Tu correo electrónico"}
                  className="min-h-12 w-full rounded-[14px] bg-transparent px-4 text-sm text-[#17233f] outline-none placeholder:text-[#7f8798] focus:ring-2 focus:ring-[#e6b18f]/60 sm:min-w-0"
                />
                <button
                  type="submit"
                  disabled={submitting}
                  className="mt-2 inline-flex min-h-12 w-full items-center justify-center rounded-[14px] bg-[#b65332] px-6 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-[#9e4629] disabled:cursor-wait disabled:opacity-70 sm:mt-0 sm:w-auto sm:whitespace-nowrap"
                >
                  {submitting ? "Registrando…" : content.buttonLabel || "Registrarme"}
                </button>
              </form>
              <div className="min-h-10 pt-3 text-xs leading-5" aria-live="polite">
                {message ? <p className="text-[#b9dfc7]">✓ {message}</p> : null}
                {error ? <p className="text-[#ffd0c2]">{error}</p> : null}
                {!message && !error ? (
                  <p className="text-white/48">Sin ruido. Solo novedades y ofertas que valgan la pena.</p>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Newsletter;
