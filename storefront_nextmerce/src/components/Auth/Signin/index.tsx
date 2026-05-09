"use client";

import Breadcrumb from "@/components/Common/Breadcrumb";
import Link from "next/link";
import React, { useState } from "react";
import { useRouter } from "next/navigation";

import { useStorefrontAuth } from "@/lib/storefront-auth";
import { loginStorefrontAccount, resolveStorefront, StorefrontApiError } from "@/lib/storefront-api";

const Signin = () => {
  const router = useRouter();
  const { signIn } = useStorefrontAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const storefront = await resolveStorefront();
      const auth = await loginStorefrontAccount(storefront.id, {
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
        setError("No pudimos iniciar sesion en este momento.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Breadcrumb title={"Iniciar sesion"} pages={["Iniciar sesion"]} />
      <section className="overflow-hidden py-20 bg-gray-2">
        <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
          <div className="max-w-[570px] w-full mx-auto rounded-xl bg-white shadow-1 p-4 sm:p-7.5 xl:p-11">
            <div className="text-center mb-11">
              <h2 className="font-semibold text-xl sm:text-2xl xl:text-heading-5 text-dark mb-1.5">
                Ingresa a tu cuenta
              </h2>
              <p>Completa tus datos para continuar con tu compra.</p>
            </div>

            <div>
              <form onSubmit={handleSubmit}>
                <div className="mb-5">
                  <label htmlFor="email" className="block mb-2.5">
                    Correo electronico
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
                    Contrasena
                  </label>

                  <input
                    type="password"
                    name="password"
                    id="password"
                    placeholder="Tu contrasena"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
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
                  {submitting ? "Ingresando..." : "Ingresar a mi cuenta"}
                </button>

                <Link
                  href="/password/reset"
                  className="block text-center text-dark-4 mt-4.5 ease-out duration-200 hover:text-dark"
                >
                  Olvidaste tu contrasena?
                </Link>

                <p className="text-center mt-6">
                  Aun no tienes cuenta?
                  <Link
                    href="/register"
                    className="text-dark ease-out duration-200 hover:text-blue pl-2"
                  >
                    Registrate aqui
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

export default Signin;
