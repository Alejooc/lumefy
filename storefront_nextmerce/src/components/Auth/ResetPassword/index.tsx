"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import Breadcrumb from "@/components/Common/Breadcrumb";
import {
  requestStorefrontPasswordRecovery,
  resetStorefrontPassword,
  resolveStorefront,
  StorefrontApiError,
} from "@/lib/storefront-api";

const ResetPassword = () => {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const storefrontIdFromQuery = searchParams.get("storefront_id") || "";
  const hasToken = Boolean(token);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleRequest = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const storefront = storefrontIdFromQuery
        ? { id: storefrontIdFromQuery }
        : await resolveStorefront();
      const response = await requestStorefrontPasswordRecovery(storefront.id, {
        email: email.trim().toLowerCase(),
      });
      setMessage(response.msg);
    } catch (err) {
      if (err instanceof StorefrontApiError) {
        setError(err.message);
      } else {
        setError("Unable to start password recovery.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setMessage(null);

    if (password !== confirmPassword) {
      setSubmitting(false);
      setError("Passwords do not match.");
      return;
    }

    try {
      const storefront = storefrontIdFromQuery
        ? { id: storefrontIdFromQuery }
        : await resolveStorefront();
      const response = await resetStorefrontPassword(storefront.id, {
        token,
        new_password: password,
      });
      setMessage(response.msg);
    } catch (err) {
      if (err instanceof StorefrontApiError) {
        setError(err.message);
      } else {
        setError("Unable to reset the password.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Breadcrumb title={"Reset Password"} pages={["Reset Password"]} />
      <section className="overflow-hidden py-20 bg-gray-2">
        <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
          <div className="max-w-[570px] w-full mx-auto rounded-xl bg-white shadow-1 p-4 sm:p-7.5 xl:p-11">
            <div className="text-center mb-11">
              <h2 className="font-semibold text-xl sm:text-2xl xl:text-heading-5 text-dark mb-1.5">
                {hasToken ? "Choose a new password" : "Recover your password"}
              </h2>
              <p>
                {hasToken
                  ? "Enter your new password below."
                  : "We will send you a recovery link if the email exists."}
              </p>
            </div>

            <form onSubmit={hasToken ? handleReset : handleRequest}>
              {!hasToken ? (
                <div className="mb-5">
                  <label htmlFor="email" className="block mb-2.5">
                    Email
                  </label>
                  <input
                    type="email"
                    id="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="Enter your email"
                    className="rounded-lg border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-3 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                  />
                </div>
              ) : (
                <>
                  <div className="mb-5">
                    <label htmlFor="password" className="block mb-2.5">
                      New Password
                    </label>
                    <input
                      type="password"
                      id="password"
                      autoComplete="new-password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="Enter your new password"
                      className="rounded-lg border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-3 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                    />
                  </div>
                  <div className="mb-5">
                    <label htmlFor="confirm-password" className="block mb-2.5">
                      Confirm Password
                    </label>
                    <input
                      type="password"
                      id="confirm-password"
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      placeholder="Confirm your new password"
                      className="rounded-lg border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-3 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                    />
                  </div>
                </>
              )}

              {error ? <p className="mb-5 text-sm text-red">{error}</p> : null}
              {message ? <p className="mb-5 text-sm text-green">{message}</p> : null}

              <button
                type="submit"
                disabled={submitting}
                className="w-full flex justify-center font-medium text-white bg-dark py-3 px-6 rounded-lg ease-out duration-200 hover:bg-blue disabled:cursor-not-allowed disabled:opacity-70"
              >
                {submitting
                  ? "Submitting..."
                  : hasToken
                    ? "Reset Password"
                    : "Send Recovery Link"}
              </button>

              <p className="text-center mt-6">
                <Link href="/login" className="text-dark ease-out duration-200 hover:text-blue">
                  Back to sign in
                </Link>
              </p>
            </form>
          </div>
        </div>
      </section>
    </>
  );
};

export default ResetPassword;
