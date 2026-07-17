"use client";

import React, { useEffect, useState } from "react";

import Breadcrumb from "../Common/Breadcrumb";
import { useStorefrontAuth } from "@/lib/storefront-auth";
import { getStorefrontBranding } from "@/lib/storefront-branding";
import {
  resolveStorefront,
  sendStorefrontContactMessage,
  StorefrontApiError,
} from "@/lib/storefront-api";

const Contact = () => {
  const { session } = useStorefrontAuth();
  const [supportName, setSupportName] = useState("Tienda");
  const [supportPhone, setSupportPhone] = useState("");
  const [supportEmail, setSupportEmail] = useState("");
  const [supportAddress, setSupportAddress] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (session?.user.full_name) {
      const parts = session.user.full_name.trim().split(/\s+/);
      setFirstName(parts[0] || "");
      setLastName(parts.slice(1).join(" "));
    }
    if (session?.user.email) {
      setEmail(session.user.email);
    }
  }, [session?.user.email, session?.user.full_name]);

  useEffect(() => {
    let active = true;

    async function loadBranding() {
      try {
        const storefront = await resolveStorefront();
        const branding = getStorefrontBranding(storefront);
        if (!active) {
          return;
        }
        setSupportName(storefront.name);
        setSupportPhone(branding.supportPhone);
        setSupportEmail(branding.supportEmail);
        setSupportAddress(branding.supportAddress);
      } catch {
        // keep defaults
      }
    }

    loadBranding();

    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const storefront = await resolveStorefront();
      const response = await sendStorefrontContactMessage(storefront.id, {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim().toLowerCase(),
        subject: subject.trim() || undefined,
        phone: phone.trim() || undefined,
        message: message.trim(),
      });
      setSuccess(response.msg);
      setSubject("");
      setPhone("");
      setMessage("");
    } catch (err) {
      if (err instanceof StorefrontApiError) {
        setError(err.message);
      } else {
        setError("No pudimos enviar tu mensaje.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Breadcrumb title={"Contacto"} pages={["Contacto"]} />

      <section className="overflow-hidden py-20 bg-gray-2">
        <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
          <div className="flex flex-col xl:flex-row gap-7.5">
            <div className="xl:max-w-[370px] w-full bg-white rounded-xl shadow-1">
              <div className="py-5 px-4 sm:px-7.5 border-b border-gray-3">
                <p className="font-medium text-xl text-dark">
                  Información de contacto
                </p>
              </div>

              <div className="p-4 sm:p-7.5">
                <div className="flex flex-col gap-4">
                  <p className="flex items-center gap-4">Tienda: {supportName}</p>
                  {supportPhone ? <p className="flex items-center gap-4">Teléfono: {supportPhone}</p> : null}
                  {supportEmail ? <p className="flex gap-4">Email: {supportEmail}</p> : null}
                  {supportAddress ? <p className="flex gap-4">Dirección: {supportAddress}</p> : null}
                </div>
              </div>
            </div>

            <div className="xl:max-w-[770px] w-full bg-white rounded-xl shadow-1 p-4 sm:p-7.5 xl:p-10">
              <form onSubmit={handleSubmit}>
                <div className="flex flex-col lg:flex-row gap-5 sm:gap-8 mb-5">
                  <div className="w-full">
                    <label htmlFor="firstName" className="block mb-2.5">
                      Nombre <span className="text-red">*</span>
                    </label>

                    <input
                      type="text"
                      name="firstName"
                      id="firstName"
                      value={firstName}
                      onChange={(event) => setFirstName(event.target.value)}
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
                      name="lastName"
                      id="lastName"
                      value={lastName}
                      onChange={(event) => setLastName(event.target.value)}
                      placeholder="Tu apellido"
                      className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                    />
                  </div>
                </div>

                <div className="flex flex-col lg:flex-row gap-5 sm:gap-8 mb-5">
                  <div className="w-full">
                    <label htmlFor="email" className="block mb-2.5">
                      Correo electrónico <span className="text-red">*</span>
                    </label>

                    <input
                      type="email"
                      name="email"
                      id="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      placeholder="tucorreo@ejemplo.com"
                      className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                    />
                  </div>

                  <div className="w-full">
                    <label htmlFor="phone" className="block mb-2.5">
                      Teléfono
                    </label>

                    <input
                      type="text"
                      name="phone"
                      id="phone"
                      value={phone}
                      onChange={(event) => setPhone(event.target.value)}
                      placeholder="Tu número de contacto"
                      className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                    />
                  </div>
                </div>

                <div className="mb-5">
                  <label htmlFor="subject" className="block mb-2.5">
                    Asunto
                  </label>

                  <input
                    type="text"
                    name="subject"
                    id="subject"
                    value={subject}
                    onChange={(event) => setSubject(event.target.value)}
                    placeholder="¿En qué podemos ayudarte?"
                    className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                  />
                </div>

                <div className="mb-7.5">
                  <label htmlFor="message" className="block mb-2.5">
                    Mensaje
                  </label>

                  <textarea
                    name="message"
                    id="message"
                    rows={5}
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    placeholder="Cuéntanos lo que necesitas"
                    className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full p-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                  ></textarea>
                </div>

                {error ? <p className="mb-5 text-sm text-red">{error}</p> : null}
                {success ? <p className="mb-5 text-sm text-green">{success}</p> : null}

                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex font-medium text-white bg-blue py-3 px-7 rounded-md ease-out duration-200 hover:bg-blue-dark disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {submitting ? "Enviando..." : "Enviar mensaje"}
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>
    </>
  );
};

export default Contact;
