"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";

import { resolveStorefront } from "@/lib/storefront-api";
import { getStorefrontBranding } from "@/lib/storefront-branding";

const socialLabels: Record<string, string> = {
  facebook: "Fb",
  twitter: "Tw",
  instagram: "Ig",
  linkedin: "In",
};

const Footer = () => {
  const year = new Date().getFullYear();
  const [supportPhone, setSupportPhone] = useState("(+099) 532-786-9843");
  const [supportEmail, setSupportEmail] = useState("support@example.com");
  const [supportAddress, setSupportAddress] = useState(
    "685 Market Street,Las Vegas, LA 95820,United States.",
  );
  const [footerText, setFooterText] = useState("All rights reserved by PimjoLabs.");
  const [socialLinks, setSocialLinks] = useState<Array<{ key: string; href: string }>>([]);
  const [helpTitle, setHelpTitle] = useState("Help & Support");
  const [accountTitle, setAccountTitle] = useState("Account");
  const [quickLinksTitle, setQuickLinksTitle] = useState("Quick Link");
  const [appTitle, setAppTitle] = useState("Download App");
  const [appDescription, setAppDescription] = useState("Exclusive savings for app users");
  const [appStoreSubtitle, setAppStoreSubtitle] = useState("Download on the");
  const [appStoreLabel, setAppStoreLabel] = useState("App Store");
  const [appStoreUrl, setAppStoreUrl] = useState<string | undefined>(undefined);
  const [playStoreSubtitle, setPlayStoreSubtitle] = useState("Get it on");
  const [playStoreLabel, setPlayStoreLabel] = useState("Google Play");
  const [playStoreUrl, setPlayStoreUrl] = useState<string | undefined>(undefined);
  const [paymentTitle, setPaymentTitle] = useState("We Accept:");
  const [showSocialLinks, setShowSocialLinks] = useState(true);
  const [showAppDownloads, setShowAppDownloads] = useState(true);
  const [showPaymentMethods, setShowPaymentMethods] = useState(true);
  const [accountLinks, setAccountLinks] = useState<Array<{ href: string; label: string }>>([]);
  const [quickLinks, setQuickLinks] = useState<Array<{ href: string; label: string }>>([]);
  const [paymentMethods, setPaymentMethods] = useState<
    Array<{ label: string; href?: string; iconUrl?: string }>
  >([]);

  useEffect(() => {
    let active = true;

    async function loadBranding() {
      try {
        const storefront = await resolveStorefront();
        const branding = getStorefrontBranding(storefront);

        if (!active) {
          return;
        }

        setSupportPhone(branding.supportPhone);
        setSupportEmail(branding.supportEmail);
        setSupportAddress(branding.supportAddress);
        setFooterText(branding.footerText);
        setSocialLinks(branding.socialLinks);
        setHelpTitle(branding.footer.helpTitle);
        setAccountTitle(branding.footer.accountTitle);
        setQuickLinksTitle(branding.footer.quickLinksTitle);
        setAppTitle(branding.footer.appTitle);
        setAppDescription(branding.footer.appDescription);
        setAppStoreSubtitle(branding.footer.appStoreSubtitle);
        setAppStoreLabel(branding.footer.appStoreLabel);
        setAppStoreUrl(branding.footer.appStoreUrl);
        setPlayStoreSubtitle(branding.footer.playStoreSubtitle);
        setPlayStoreLabel(branding.footer.playStoreLabel);
        setPlayStoreUrl(branding.footer.playStoreUrl);
        setPaymentTitle(branding.footer.paymentTitle);
        setShowSocialLinks(branding.footer.showSocialLinks);
        setShowAppDownloads(branding.footer.showAppDownloads);
        setShowPaymentMethods(branding.footer.showPaymentMethods);
        setAccountLinks(branding.footer.accountLinks);
        setQuickLinks(branding.footer.quickLinks);
        setPaymentMethods(branding.footer.paymentMethods);
      } catch {
        // keep template defaults when storefront branding is unavailable
      }
    }

    loadBranding();

    return () => {
      active = false;
    };
  }, []);

  return (
    <footer className="overflow-hidden">
      <div className="max-w-[1170px] mx-auto px-4 sm:px-8 xl:px-0">
        <div className="flex flex-wrap xl:flex-nowrap gap-10 xl:gap-19 xl:justify-between pt-17.5 xl:pt-22.5 pb-10 xl:pb-15">
          <div className="max-w-[330px] w-full">
            <h2 className="mb-7.5 text-custom-1 font-medium text-dark">
              {helpTitle}
            </h2>

            <ul className="flex flex-col gap-3">
              <li>{supportAddress}</li>
              <li>
                <a href={`tel:${supportPhone}`} className="ease-out duration-200 hover:text-blue">
                  {supportPhone}
                </a>
              </li>
              <li>
                <a
                  href={`mailto:${supportEmail}`}
                  className="ease-out duration-200 hover:text-blue"
                >
                  {supportEmail}
                </a>
              </li>
            </ul>

            {showSocialLinks && socialLinks.length > 0 ? (
              <div className="flex items-center gap-4 mt-7.5">
                {socialLinks.map((social) => (
                  <a
                    key={social.key}
                    href={social.href}
                    aria-label={`${social.key} Social Link`}
                    className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-3 ease-out duration-200 hover:border-blue hover:text-blue"
                    target="_blank"
                    rel="noreferrer"
                  >
                    {socialLabels[social.key] || social.key.slice(0, 2)}
                  </a>
                ))}
              </div>
            ) : null}
          </div>

          <div className="w-full sm:w-auto">
            <h2 className="mb-7.5 text-custom-1 font-medium text-dark">
              {accountTitle}
            </h2>

            <ul className="flex flex-col gap-3.5">
              {accountLinks.map((item) => (
                <li key={item.label}>
                  <Link className="ease-out duration-200 hover:text-blue" href={item.href}>
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="w-full sm:w-auto">
            <h2 className="mb-7.5 text-custom-1 font-medium text-dark">
              {quickLinksTitle}
            </h2>

            <ul className="flex flex-col gap-3">
              {quickLinks.map((item) => (
                <li key={item.label}>
                  <Link className="ease-out duration-200 hover:text-blue" href={item.href}>
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {showAppDownloads ? (
            <div className="w-full sm:w-auto">
            <h2 className="mb-7.5 text-custom-1 font-medium text-dark lg:text-right">
              {appTitle}
            </h2>

            <p className="lg:text-right text-custom-sm mb-4">
              {appDescription}
            </p>

            <ul className="flex flex-col lg:items-end gap-3">
              <li>
                <a
                  className="inline-flex items-center gap-3 py-[9px] pl-4 pr-7.5 text-white rounded-md bg-dark ease-out duration-200 hover:bg-opacity-95"
                  href={appStoreUrl || "#"}
                >
                  <div>
                    <span className="block text-custom-xs">
                      {appStoreSubtitle}
                    </span>
                    <p className="font-medium">{appStoreLabel}</p>
                  </div>
                </a>
              </li>

              <li>
                <a
                  className="inline-flex items-center gap-3 py-[9px] pl-4 pr-8.5 text-white rounded-md bg-blue ease-out duration-200 hover:bg-opacity-95"
                  href={playStoreUrl || "#"}
                >
                  <div>
                    <span className="block text-custom-xs">{playStoreSubtitle}</span>
                    <p className="font-medium">{playStoreLabel}</p>
                  </div>
                </a>
              </li>
            </ul>
            </div>
          ) : null}
        </div>
      </div>

      <div className="py-5 xl:py-7.5 bg-gray-1">
        <div className="max-w-[1170px] mx-auto px-4 sm:px-8 xl:px-0">
          <div className="flex gap-5 flex-wrap items-center justify-between">
            <p className="text-dark font-medium">
              &copy; {year}. {footerText}
            </p>

            {showPaymentMethods && paymentMethods.length > 0 ? (
              <div className="flex flex-wrap items-center gap-4">
                <p className="font-medium">{paymentTitle}</p>

                <div className="flex flex-wrap items-center gap-6">
                  {paymentMethods.map((method) => {
                    const content = method.iconUrl ? (
                      <img
                        src={method.iconUrl}
                        alt={method.label}
                        className="max-h-6 w-auto object-contain"
                      />
                    ) : (
                      <span className="text-sm font-medium text-dark">{method.label}</span>
                    );

                    return method.href ? (
                      <a
                        key={`${method.label}-${method.iconUrl || "text"}`}
                        href={method.href}
                        aria-label={`payment method ${method.label}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {content}
                      </a>
                    ) : (
                      <div key={`${method.label}-${method.iconUrl || "text"}`} aria-label={`payment method ${method.label}`}>
                        {content}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
