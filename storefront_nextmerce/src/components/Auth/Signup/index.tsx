"use client";

import Breadcrumb from "@/components/Common/Breadcrumb";
import Link from "next/link";
import React, { useState } from "react";
import { useRouter } from "next/navigation";

import { useStorefrontAuth } from "@/lib/storefront-auth";
import {
  registerStorefrontAccount,
  resolveStorefront,
  StorefrontApiError,
} from "@/lib/storefront-api";

const Signup = () => {
  const router = useRouter();
  const { signIn } = useStorefrontAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Las contrasenas no coinciden.");
      return;
    }

    setSubmitting(true);
    try {
      const storefront = await resolveStorefront();
      const auth = await registerStorefrontAccount(storefront.id, {
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        password,
      });

      signIn({
        token: auth.access_token,
        storefrontId: storefront.id,
        user: auth.user,
      });
      router.push("/account");
    } catch (err) {
      if (err instanceof StorefrontApiError) {
        setError(err.message);
      } else {
        setError("No pudimos crear tu cuenta en este momento.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Breadcrumb title={"Crear cuenta"} pages={["Crear cuenta"]} />
      <section className="overflow-hidden py-20 bg-gray-2">
        <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
          <div className="max-w-[570px] w-full mx-auto rounded-xl bg-white shadow-1 p-4 sm:p-7.5 xl:p-11">
            <div className="text-center mb-11">
              <h2 className="font-semibold text-xl sm:text-2xl xl:text-heading-5 text-dark mb-1.5">
                Crea tu cuenta
              </h2>
              <p>Completa tus datos para comprar y hacer seguimiento a tus pedidos.</p>
            </div>

            <div className="mt-5.5">
              <form onSubmit={handleSubmit}>
                <div className="mb-5">
                  <label htmlFor="name" className="block mb-2.5">
                    Nombre completo <span className="text-red">*</span>
                  </label>

                  <input
                    type="text"
                    name="name"
                    id="name"
                    placeholder="Tu nombre completo"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    className="rounded-lg border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-3 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                  />
                </div>

                <div className="mb-5">
                  <label htmlFor="email" className="block mb-2.5">
                    Correo electronico <span className="text-red">*</span>
                  </label>

                  <input
                    type="email"
                    name="email"
                    id="email"
                    placeholder="Tu correo electronico"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="rounded-lg border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-3 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                  />
                </div>

                <div className="mb-5">
                  <label htmlFor="password" className="block mb-2.5">
                    Contrasena <span className="text-red">*</span>
                  </label>

                  <input
                    type="password"
                    name="password"
                    id="password"
                    placeholder="Crea una contrasena"
                    autoComplete="new-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="rounded-lg border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-3 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                  />
                </div>

                <div className="mb-5.5">
                  <label htmlFor="re-type-password" className="block mb-2.5">
                    Confirma tu contrasena <span className="text-red">*</span>
                  </label>

                  <input
                    type="password"
                    name="re-type-password"
                    id="re-type-password"
                    placeholder="Vuelve a escribir tu contrasena"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    className="rounded-lg border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-3 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                  />
                </div>

                {error ? (
                  <p className="rounded-lg border border-red-light-4 bg-red-light-6 px-4 py-3 text-sm text-red">
                    {error}
                  </p>
                ) : null}

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full flex justify-center font-medium text-white bg-dark py-3 px-6 rounded-lg ease-out duration-200 hover:bg-blue mt-7.5 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {submitting ? "Creando cuenta..." : "Crear cuenta"}
                </button>

                <p className="text-center mt-6">
                  Ya tienes cuenta?
                  <Link
                    href="/login"
                    className="text-dark ease-out duration-200 hover:text-blue pl-2"
                  >
                    Inicia sesion
                  </Link>
                </p>
              </form>
            </div>
          </div>
        </div>
      </section>
    </>
  );
};

export default Signup;
