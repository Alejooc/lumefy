"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import Breadcrumb from "../Common/Breadcrumb";
import Orders from "../Orders";
import { useStorefrontAuth } from "@/lib/storefront-auth";
import {
  changeStorefrontAccountPassword,
  resolveStorefront,
  StorefrontApiError,
  updateStorefrontAccountProfile,
} from "@/lib/storefront-api";

const MyAccount = () => {
  const router = useRouter();
  const { session, loading, refreshSession, signOut } = useStorefrontAuth();
  const [activeTab, setActiveTab] = useState("dashboard");
  const [fullName, setFullName] = useState("");
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    if (!loading && !session) {
      router.replace("/login");
    }
  }, [loading, router, session]);

  useEffect(() => {
    setFullName(session?.user.full_name || "");
  }, [session?.user.full_name]);

  if (loading || !session) {
    return (
      <>
        <Breadcrumb title={"Mi cuenta"} pages={["Mi cuenta"]} />
        <section className="overflow-hidden py-20 bg-gray-2">
          <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
            <div className="rounded-xl bg-white shadow-1 py-9.5 px-4 sm:px-7.5 xl:px-10">
              Cargando tu cuenta...
            </div>
          </div>
        </section>
      </>
    );
  }

  const handleLogout = () => {
    signOut();
    router.push("/login");
  };

  const handleProfileSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSavingProfile(true);
    setProfileError(null);
    setProfileMessage(null);

    try {
      const storefront = await resolveStorefront();
      await updateStorefrontAccountProfile(storefront.id, session.token, {
        full_name: fullName.trim(),
      });
      await refreshSession();
      setProfileMessage("Account details updated successfully.");
    } catch (err) {
      if (err instanceof StorefrontApiError) {
        setProfileError(err.message);
      } else {
        setProfileError("Unable to update your account.");
      }
    } finally {
      setSavingProfile(false);
    }
  };

  const handlePasswordSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPasswordError(null);
    setPasswordMessage(null);

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }

    setSavingPassword(true);
    try {
      const storefront = await resolveStorefront();
      const response = await changeStorefrontAccountPassword(storefront.id, session.token, {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordMessage(response.msg);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      if (err instanceof StorefrontApiError) {
        setPasswordError(err.message);
      } else {
        setPasswordError("Unable to change your password.");
      }
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <>
      <Breadcrumb title={"Account"} pages={["Account"]} />

      <section className="overflow-hidden py-20 bg-gray-2">
        <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
          <div className="flex flex-col xl:flex-row gap-7.5">
            <div className="xl:max-w-[370px] w-full bg-white rounded-xl shadow-1">
              <div className="p-4 sm:p-7.5 xl:p-9">
                <div className="mb-7 rounded-lg bg-gray-1 px-5 py-4">
                  <p className="font-medium text-dark mb-0.5">
                    {session.user.full_name || "Storefront Customer"}
                  </p>
                  <p className="text-custom-xs">{session.user.email}</p>
                </div>

                <div className="flex flex-wrap xl:flex-nowrap xl:flex-col gap-4">
                  {[
                    ["dashboard", "Dashboard"],
                    ["orders", "Orders"],
                    ["account-details", "Account Details"],
                  ].map(([key, label]) => (
                    <button
                      key={key}
                      onClick={() => setActiveTab(key)}
                      className={`flex items-center rounded-md gap-2.5 py-3 px-4.5 ease-out duration-200 hover:bg-blue hover:text-white ${
                        activeTab === key ? "text-white bg-blue" : "text-dark-2 bg-gray-1"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                  <button
                    onClick={handleLogout}
                    className="flex items-center rounded-md gap-2.5 py-3 px-4.5 ease-out duration-200 text-dark-2 bg-gray-1 hover:bg-blue hover:text-white"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>

            <div
              className={`xl:max-w-[770px] w-full bg-white rounded-xl shadow-1 py-9.5 px-4 sm:px-7.5 xl:px-10 ${
                activeTab === "dashboard" ? "block" : "hidden"
              }`}
            >
              <p className="text-dark">
                Hello {session.user.full_name || session.user.email} (
                <button
                  onClick={handleLogout}
                  className="text-red ease-out duration-200 hover:underline"
                >
                  Log Out
                </button>
                )
              </p>

              <p className="text-custom-sm mt-4">
                From your account dashboard you can view your recent orders and edit
                your account details securely.
              </p>
            </div>

            <div
              className={`xl:max-w-[770px] w-full bg-white rounded-xl shadow-1 ${
                activeTab === "orders" ? "block" : "hidden"
              }`}
            >
              <Orders />
            </div>

            <div
              className={`xl:max-w-[770px] w-full ${
                activeTab === "account-details" ? "block" : "hidden"
              }`}
            >
              <form onSubmit={handleProfileSubmit}>
                <div className="bg-white shadow-1 rounded-xl p-4 sm:p-8.5">
                  <div className="mb-5">
                    <label htmlFor="fullName" className="block mb-2.5">
                      Full Name <span className="text-red">*</span>
                    </label>

                    <input
                      type="text"
                      name="fullName"
                      id="fullName"
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                    />
                  </div>

                  <div className="mb-5">
                    <label htmlFor="emailAddress" className="block mb-2.5">
                      Email Address
                    </label>

                    <input
                      type="email"
                      name="emailAddress"
                      id="emailAddress"
                      value={session.user.email}
                      disabled
                      className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none opacity-70"
                    />
                  </div>

                  {profileError ? <p className="mb-5 text-sm text-red">{profileError}</p> : null}
                  {profileMessage ? <p className="mb-5 text-sm text-green">{profileMessage}</p> : null}

                  <button
                    type="submit"
                    disabled={savingProfile}
                    className="inline-flex font-medium text-white bg-blue py-3 px-7 rounded-md ease-out duration-200 hover:bg-blue-dark disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {savingProfile ? "Saving..." : "Save Changes"}
                  </button>
                </div>
              </form>

              <p className="text-custom-sm mt-5 mb-9">
                This is how your name will be displayed in your account.
              </p>

              <p className="font-medium text-xl sm:text-2xl text-dark mb-7">
                Password Change
              </p>

              <form onSubmit={handlePasswordSubmit}>
                <div className="bg-white shadow-1 rounded-xl p-4 sm:p-8.5">
                  <div className="mb-5">
                    <label htmlFor="oldPassword" className="block mb-2.5">
                      Current Password
                    </label>

                    <input
                      type="password"
                      name="oldPassword"
                      id="oldPassword"
                      autoComplete="current-password"
                      value={currentPassword}
                      onChange={(event) => setCurrentPassword(event.target.value)}
                      className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                    />
                  </div>

                  <div className="mb-5">
                    <label htmlFor="newPassword" className="block mb-2.5">
                      New Password
                    </label>

                    <input
                      type="password"
                      name="newPassword"
                      id="newPassword"
                      autoComplete="new-password"
                      value={newPassword}
                      onChange={(event) => setNewPassword(event.target.value)}
                      className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                    />
                  </div>

                  <div className="mb-5">
                    <label htmlFor="confirmNewPassword" className="block mb-2.5">
                      Confirm New Password
                    </label>

                    <input
                      type="password"
                      name="confirmNewPassword"
                      id="confirmNewPassword"
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      className="rounded-md border border-gray-3 bg-gray-1 placeholder:text-dark-5 w-full py-2.5 px-5 outline-none duration-200 focus:border-transparent focus:shadow-input focus:ring-2 focus:ring-blue/20"
                    />
                  </div>

                  {passwordError ? <p className="mb-5 text-sm text-red">{passwordError}</p> : null}
                  {passwordMessage ? <p className="mb-5 text-sm text-green">{passwordMessage}</p> : null}

                  <button
                    type="submit"
                    disabled={savingPassword}
                    className="inline-flex font-medium text-white bg-blue py-3 px-7 rounded-md ease-out duration-200 hover:bg-blue-dark disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {savingPassword ? "Updating..." : "Change Password"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </section>
    </>
  );
};

export default MyAccount;
