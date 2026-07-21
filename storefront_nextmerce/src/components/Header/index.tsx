"use client";
import React, { useState, useEffect } from "react";
import Link from "next/link";
import { menuData } from "./menuData";
import Dropdown from "./Dropdown";
import { useAppSelector } from "@/redux/store";
import { useSelector } from "react-redux";
import { selectTotalPrice } from "@/redux/features/cart-slice";
import { useCartModalContext } from "@/app/context/CartSidebarModalContext";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  getPublicCollections,
  getPublicNavigation,
  resolveStorefront,
} from "@/lib/storefront-api";
import { buildHeaderMenu } from "@/lib/navigation";
import { getStorefrontBranding } from "@/lib/storefront-branding";
import { useStorefrontAuth } from "@/lib/storefront-auth";
import { useStorefrontCurrency } from "@/lib/storefront-currency";
import { Menu } from "@/types/Menu";
import SearchModal from "./SearchModal";

const Header = () => {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchModalOpen, setSearchModalOpen] = useState(false);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [mobileOpenSubmenu, setMobileOpenSubmenu] = useState<number | null>(null);
  const [stickyMenu, setStickyMenu] = useState(false);
  const [menuItems, setMenuItems] = useState<Menu[]>(menuData);
  const [logoUrl, setLogoUrl] = useState<string | undefined>(undefined);
  const [supportPhone, setSupportPhone] = useState("");
  const [supportLabel, setSupportLabel] = useState("Atención al cliente");
  const [searchPlaceholder, setSearchPlaceholder] = useState("Buscar productos...");
  const [accountHeading, setAccountHeading] = useState("cuenta");
  const [guestAccountLabel, setGuestAccountLabel] = useState("Ingresar");
  const [signOutLabel, setSignOutLabel] = useState("Cerrar sesión");
  const [cartHeading, setCartHeading] = useState("carrito");
  const [recentlyViewedLabel, setRecentlyViewedLabel] = useState("Vistos recientemente");
  const [wishlistLabel, setWishlistLabel] = useState("Favoritos");
  const { openCartModal } = useCartModalContext();
  const { session, signOut } = useStorefrontAuth();
  const { format } = useStorefrontCurrency();

  const product = useAppSelector((state) => state.cartReducer.items);
  const totalPrice = useSelector(selectTotalPrice);

  const handleOpenCartModal = () => {
    openCartModal();
  };

  // Sticky menu
  const handleStickyMenu = () => {
    if (window.scrollY >= 80) {
      setStickyMenu(true);
    } else {
      setStickyMenu(false);
    }
  };

  useEffect(() => {
    window.addEventListener("scroll", handleStickyMenu);

    return () => {
      window.removeEventListener("scroll", handleStickyMenu);
    };
  }, []);

  useEffect(() => {
    if (!navigationOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [navigationOpen]);

  useEffect(() => {
    let active = true;

    async function loadNavigation() {
      try {
        const storefront = await resolveStorefront();
        const branding = getStorefrontBranding(storefront);
        const [navigation, collections] = await Promise.all([
          getPublicNavigation(storefront.id),
          getPublicCollections(storefront.id),
        ]);

        if (!active) {
          return;
        }

        setLogoUrl(branding.logoUrl);
        setSupportPhone(branding.supportPhone);
        setSupportLabel(branding.header.supportLabel);
        setSearchPlaceholder(branding.header.searchPlaceholder);
        setAccountHeading(branding.header.accountHeading);
        setGuestAccountLabel(branding.header.guestAccountLabel);
        setSignOutLabel(branding.header.signOutLabel);
        setCartHeading(branding.header.cartHeading);
        setRecentlyViewedLabel(branding.header.recentlyViewedLabel);
        setWishlistLabel(branding.header.wishlistLabel);

        if (!navigation.length) {
          return;
        }

        setMenuItems(buildHeaderMenu(navigation, collections));
      } catch {
        // keep template fallback menu when backend navigation is not available
      }
    }

    loadNavigation();

    return () => {
      active = false;
    };
  }, []);

  const handleSearchSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const params = new URLSearchParams();
    const query = searchQuery.trim();

    if (query) {
      params.set("q", query);
    }

    if (!query) {
      router.push(params.toString() ? `/products?${params.toString()}` : "/products");
      return;
    }

    setSearchModalOpen(true);
  };

  const handleSignOut = () => {
    signOut();
    router.push("/login");
  };

  return (
    <header
      className={`fixed left-0 top-0 w-full z-9999 bg-white transition-all ease-in-out duration-300 ${
        stickyMenu && "shadow"
      }`}
    >
      <SearchModal
        isOpen={searchModalOpen}
        initialQuery={searchQuery}
        onClose={() => setSearchModalOpen(false)}
      />

      <div
        className={`fixed inset-0 z-[100001] xl:hidden transition-all duration-300 ${
          navigationOpen ? "visible bg-dark/60" : "invisible bg-transparent"
        }`}
        onClick={() => {
          setNavigationOpen(false);
          setMobileOpenSubmenu(null);
        }}
      >
        <aside
          className={`absolute right-0 top-0 flex h-full w-full max-w-[340px] flex-col bg-white shadow-2 transition-transform duration-300 ${
            navigationOpen ? "translate-x-0" : "translate-x-full"
          }`}
          onClick={(event) => event.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-gray-3 px-5 py-5">
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-[0.18em] text-dark-4">
                Navegacion
              </p>
              <h2 className="text-lg font-semibold text-dark">Menu</h2>
            </div>

            <button
              type="button"
              onClick={() => {
                setNavigationOpen(false);
                setMobileOpenSubmenu(null);
              }}
              aria-label="Cerrar menu"
              className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-3 text-dark transition hover:border-blue hover:text-blue"
            >
              <svg className="fill-current" width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M4.78 3.72 9 7.94l4.22-4.22 1.06 1.06L10.06 9l4.22 4.22-1.06 1.06L9 10.06l-4.22 4.22-1.06-1.06L7.94 9 3.72 4.78l1.06-1.06Z" />
              </svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-5">
            <div className="mb-5 rounded-2xl bg-gray-1 p-4">
              <p className="mb-1 text-xs font-medium uppercase tracking-[0.18em] text-dark-4">
                {accountHeading}
              </p>
              <p className="mb-3 text-base font-semibold text-dark">
                {session ? session.user.full_name || "Mi cuenta" : guestAccountLabel}
              </p>

              <div className="flex gap-2.5">
                <Link
                  href={session ? "/account" : "/login"}
                  onClick={() => {
                    setNavigationOpen(false);
                    setMobileOpenSubmenu(null);
                  }}
                  className="inline-flex flex-1 items-center justify-center rounded-xl bg-white px-4 py-3 text-sm font-medium text-dark transition hover:text-blue"
                >
                  {session ? "Ver cuenta" : "Ingresar"}
                </Link>

                {session ? (
                  <button
                    type="button"
                    onClick={() => {
                      handleSignOut();
                      setNavigationOpen(false);
                      setMobileOpenSubmenu(null);
                    }}
                    className="inline-flex flex-1 items-center justify-center rounded-xl border border-gray-3 px-4 py-3 text-sm font-medium text-dark transition hover:border-blue hover:text-blue"
                  >
                    {signOutLabel}
                  </button>
                ) : null}
              </div>
            </div>

            <nav>
              <ul className="flex flex-col gap-2">
                {menuItems.map((menuItem) =>
                  menuItem.submenu?.length ? (
                    <li key={menuItem.id} className="rounded-2xl border border-gray-3 bg-gray-1">
                      <button
                        type="button"
                        onClick={() =>
                          setMobileOpenSubmenu((current) =>
                            current === menuItem.id ? null : menuItem.id,
                          )
                        }
                        className="flex w-full items-center justify-between px-4 py-3 text-left font-medium text-dark"
                      >
                        <span>{menuItem.title}</span>
                        <svg
                          className={`fill-current transition-transform duration-200 ${
                            mobileOpenSubmenu === menuItem.id ? "rotate-180" : ""
                          }`}
                          width="16"
                          height="16"
                          viewBox="0 0 16 16"
                          fill="none"
                        >
                          <path
                            fillRule="evenodd"
                            clipRule="evenodd"
                            d="M2.95363 5.67461C3.13334 5.46495 3.44899 5.44067 3.65866 5.62038L7.99993 9.34147L12.3412 5.62038C12.5509 5.44067 12.8665 5.46495 13.0462 5.67461C13.2259 5.88428 13.2017 6.19993 12.992 6.37964L8.32532 10.3796C8.13808 10.5401 7.86178 10.5401 7.67453 10.3796L3.00787 6.37964C2.7982 6.19993 2.77392 5.88428 2.95363 5.67461Z"
                            fill=""
                          />
                        </svg>
                      </button>

                      <div
                        className={`grid transition-all duration-300 ${
                          mobileOpenSubmenu === menuItem.id
                            ? "grid-rows-[1fr] border-t border-gray-3"
                            : "grid-rows-[0fr]"
                        }`}
                      >
                        <div className="overflow-hidden">
                          <div className="flex flex-col px-3 py-3">
                            {menuItem.submenu.map((item) => (
                              <Link
                                key={item.id}
                                href={item.path || "/"}
                                onClick={() => {
                                  setNavigationOpen(false);
                                  setMobileOpenSubmenu(null);
                                }}
                                className="rounded-xl px-3 py-2.5 text-sm text-dark transition hover:bg-white hover:text-blue"
                              >
                                {item.title}
                              </Link>
                            ))}
                          </div>
                        </div>
                      </div>
                    </li>
                  ) : (
                    <li key={menuItem.id}>
                      <Link
                        href={menuItem.path || "/"}
                        onClick={() => {
                          setNavigationOpen(false);
                          setMobileOpenSubmenu(null);
                        }}
                        className="flex items-center justify-between rounded-2xl border border-gray-3 bg-gray-1 px-4 py-3 font-medium text-dark transition hover:bg-white hover:text-blue"
                      >
                        <span>{menuItem.title}</span>
                        <svg
                          className="fill-current"
                          width="14"
                          height="14"
                          viewBox="0 0 14 14"
                          fill="none"
                        >
                          <path
                            d="M4.05806 11.3581C3.814 11.114 3.814 10.7183 4.05806 10.4742L7.53232 7L4.05806 3.52574C3.814 3.28169 3.814 2.88595 4.05806 2.64189C4.30213 2.39782 4.69786 2.39782 4.94193 2.64189L8.85811 6.55806C9.10217 6.80213 9.10217 7.19787 8.85811 7.44194L4.94193 11.3581C4.69786 11.6022 4.30213 11.6022 4.05806 11.3581Z"
                            fill=""
                          />
                        </svg>
                      </Link>
                    </li>
                  ),
                )}
              </ul>
            </nav>
          </div>

          <div className="border-t border-gray-3 bg-gray-1 px-5 py-4">
            <div className="mb-4 grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => {
                  setNavigationOpen(false);
                  setMobileOpenSubmenu(null);
                  handleOpenCartModal();
                }}
                className="flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-medium text-dark transition hover:text-blue"
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  className="text-blue"
                >
                  <path
                    d="M15.5433 9.5172C15.829 9.21725 15.8174 8.74252 15.5174 8.45686C15.2175 8.17119 14.7428 8.18277 14.4571 8.48272L12.1431 10.9125L11.5433 10.2827C11.2576 9.98277 10.7829 9.97119 10.483 10.2569C10.183 10.5425 10.1714 11.0173 10.4571 11.3172L11.6 12.5172C11.7415 12.6658 11.9378 12.75 12.1431 12.75C12.3483 12.75 12.5446 12.6658 12.6862 12.5172L15.5433 9.5172Z"
                    fill="currentColor"
                  />
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M1.29266 2.7512C1.43005 2.36044 1.8582 2.15503 2.24896 2.29242L2.55036 2.39838C3.16689 2.61511 3.69052 2.79919 4.10261 3.00139C4.54324 3.21759 4.92109 3.48393 5.20527 3.89979C5.48725 4.31243 5.60367 4.76515 5.6574 5.26153C5.66124 5.29706 5.6648 5.33321 5.66809 5.36996L17.1203 5.36996C17.9389 5.36995 18.7735 5.36993 19.4606 5.44674C19.8103 5.48584 20.1569 5.54814 20.4634 5.65583C20.7639 5.76141 21.0942 5.93432 21.3292 6.23974C21.711 6.73613 21.7777 7.31414 21.7416 7.90034C21.7071 8.45845 21.5686 9.15234 21.4039 9.97723L21.3935 10.0295L21.3925 10.0341L20.8836 12.5033C20.7339 13.2298 20.6079 13.841 20.4455 14.3231C20.2731 14.8346 20.0341 15.2842 19.6076 15.6318C19.1811 15.9793 18.6925 16.1226 18.1568 16.1882C17.6518 16.25 17.0278 16.25 16.2862 16.25L10.8804 16.25C9.53464 16.25 8.44479 16.25 7.58656 16.1283C6.69032 16.0012 5.93752 15.7285 5.34366 15.1022C4.79742 14.526 4.50529 13.9144 4.35897 13.0601C4.22191 12.2598 4.20828 11.2125 4.20828 9.75996V7.03832C4.20828 6.29837 4.20726 5.80316 4.16611 5.42295C4.12678 5.0596 4.05708 4.87818 3.96682 4.74609C3.87876 4.61723 3.74509 4.4968 3.44186 4.34802C3.11902 4.18961 2.68026 4.03406 2.01266 3.79934L1.75145 3.7075C1.36068 3.57012 1.15527 3.14197 1.29266 2.7512Z"
                    fill="currentColor"
                  />
                </svg>
                <span>Carrito ({product.length})</span>
              </button>

              <Link
                href="/wishlist"
                onClick={() => {
                  setNavigationOpen(false);
                  setMobileOpenSubmenu(null);
                }}
                className="flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-medium text-dark transition hover:text-blue"
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 16 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  className="text-blue"
                >
                  <path
                    d="M5.97441 12.6073L6.43872 12.0183L5.97441 12.6073ZM7.99992 3.66709L7.45955 4.18719C7.60094 4.33408 7.79604 4.41709 7.99992 4.41709C8.2038 4.41709 8.3989 4.33408 8.54028 4.18719L7.99992 3.66709ZM10.0254 12.6073L10.4897 13.1962L10.0254 12.6073ZM6.43872 12.0183C5.41345 11.21 4.33627 10.4524 3.47904 9.48717C2.64752 8.55085 2.08325 7.47831 2.08325 6.0914H0.583252C0.583252 7.94644 1.3588 9.35867 2.35747 10.4832C3.33043 11.5788 4.57383 12.4582 5.51009 13.1962L6.43872 12.0183ZM2.08325 6.0914C2.08325 4.75102 2.84027 3.63995 3.85342 3.17683C4.81929 2.73533 6.15155 2.82823 7.45955 4.18719L8.54028 3.14699C6.84839 1.38917 4.84732 1.07324 3.22983 1.8126C1.65962 2.53035 0.583252 4.18982 0.583252 6.0914H2.08325ZM5.51009 13.1962C5.84928 13.4636 6.22932 13.7618 6.61834 13.9891C7.00711 14.2163 7.47619 14.4167 7.99992 14.4167V12.9167C7.85698 12.9167 7.65939 12.8601 7.37512 12.694C7.0911 12.5281 6.79171 12.2965 6.43872 12.0183L5.51009 13.1962ZM10.4897 13.1962C11.426 12.4582 12.6694 11.5788 13.6424 10.4832C14.641 9.35867 15.4166 7.94644 15.4166 6.0914H13.9166C13.9166 7.47831 13.3523 8.55085 12.5208 9.48717C11.6636 10.4524 10.5864 11.21 9.56112 12.0183L10.4897 13.1962ZM15.4166 6.0914C15.4166 4.18982 14.3402 2.53035 12.77 1.8126C11.1525 1.07324 9.15145 1.38917 7.45955 3.14699L8.54028 4.18719C9.84828 2.82823 11.1805 2.73533 12.1464 3.17683C13.1596 3.63995 13.9166 4.75102 13.9166 6.0914H15.4166ZM9.56112 12.0183C9.20813 12.2965 8.90874 12.5281 8.62471 12.694C8.34044 12.8601 8.14285 12.9167 7.99992 12.9167V14.4167C8.52365 14.4167 8.99273 14.2163 9.3815 13.9891C9.77052 13.7618 10.1506 13.4636 10.4897 13.1962L9.56112 12.0183Z"
                    fill="currentColor"
                  />
                </svg>
                <span>Favoritos</span>
              </Link>
            </div>

            {supportPhone ? <>
              <p className="mb-1 text-xs font-medium uppercase tracking-[0.18em] text-dark-4">
                {supportLabel}
              </p>
              <p className="text-sm font-medium text-dark">{supportPhone}</p>
            </> : null}
          </div>
        </aside>
      </div>

      <div className="max-w-[1170px] mx-auto px-4 sm:px-7.5 xl:px-0">
        {/* <!-- header top start --> */}
        <div
          className={`flex flex-col gap-4 lg:flex-row lg:items-center xl:justify-between ease-out duration-200 ${
            stickyMenu ? "py-4" : "py-5"
          }`}
        >
          {/* <!-- header top left --> */}
          <div className="w-full flex flex-col gap-4 lg:grid lg:grid-cols-[auto_minmax(420px,560px)] lg:items-center lg:gap-8 xl:grid-cols-[auto_minmax(500px,620px)]">
            <div className="flex w-full items-center justify-between gap-3 lg:w-auto lg:justify-start lg:min-w-[182px]">
              <Link className="flex-shrink-0" href="/">
                <Image
                  src={logoUrl || "/images/logo/logo.svg"}
                  alt="Lumefy"
                  width={182}
                  height={30}
                  className="h-auto w-[150px] sm:w-[170px] lg:w-[182px]"
                />
              </Link>

              <div className="flex items-center gap-3 lg:hidden">
                <Link
                  href={session ? "/account" : "/login"}
                  className="flex h-10 w-10 items-center justify-center rounded-full border border-blue/20 bg-blue/5 text-blue transition hover:border-blue hover:bg-blue hover:text-white"
                  aria-label="Mi cuenta"
                >
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      fillRule="evenodd"
                      clipRule="evenodd"
                      d="M12 1.25C9.37666 1.25 7.25001 3.37665 7.25001 6C7.25001 8.62335 9.37666 10.75 12 10.75C14.6234 10.75 16.75 8.62335 16.75 6C16.75 3.37665 14.6234 1.25 12 1.25ZM8.75001 6C8.75001 4.20507 10.2051 2.75 12 2.75C13.7949 2.75 15.25 4.20507 15.25 6C15.25 7.79493 13.7949 9.25 12 9.25C10.2051 9.25 8.75001 7.79493 8.75001 6Z"
                      fill="currentColor"
                    />
                    <path
                      fillRule="evenodd"
                      clipRule="evenodd"
                      d="M12 12.25C9.68646 12.25 7.55494 12.7759 5.97546 13.6643C4.4195 14.5396 3.25001 15.8661 3.25001 17.5L3.24995 17.602C3.24882 18.7638 3.2474 20.222 4.52642 21.2635C5.15589 21.7761 6.03649 22.1406 7.22622 22.3815C8.41927 22.6229 9.97424 22.75 12 22.75C14.0258 22.75 15.5808 22.6229 16.7738 22.3815C17.9635 22.1406 18.8441 21.7761 19.4736 21.2635C20.7526 20.222 20.7512 18.7638 20.7501 17.602L20.75 17.5C20.75 15.8661 19.5805 14.5396 18.0246 13.6643C16.4451 12.7759 14.3136 12.25 12 12.25ZM4.75001 17.5C4.75001 16.6487 5.37139 15.7251 6.71085 14.9717C8.02681 14.2315 9.89529 13.75 12 13.75C14.1047 13.75 15.9732 14.2315 17.2892 14.9717C18.6286 15.7251 19.25 16.6487 19.25 17.5C19.25 18.8078 19.2097 19.544 18.5264 20.1004C18.1559 20.4022 17.5365 20.6967 16.4762 20.9113C15.4193 21.1252 13.9742 21.25 12 21.25C10.0258 21.25 8.58075 21.1252 7.5238 20.9113C6.46354 20.6967 5.84413 20.4022 5.4736 20.1004C4.79033 19.544 4.75001 18.8078 4.75001 17.5Z"
                      fill="currentColor"
                    />
                  </svg>
                </Link>

                <button
                  onClick={handleOpenCartModal}
                  className="relative flex h-10 w-10 items-center justify-center rounded-full border border-blue/20 bg-blue/5 text-blue transition hover:border-blue hover:bg-blue hover:text-white"
                  aria-label="Carrito"
                >
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M15.5433 9.5172C15.829 9.21725 15.8174 8.74252 15.5174 8.45686C15.2175 8.17119 14.7428 8.18277 14.4571 8.48272L12.1431 10.9125L11.5433 10.2827C11.2576 9.98277 10.7829 9.97119 10.483 10.2569C10.183 10.5425 10.1714 11.0173 10.4571 11.3172L11.6 12.5172C11.7415 12.6658 11.9378 12.75 12.1431 12.75C12.3483 12.75 12.5446 12.6658 12.6862 12.5172L15.5433 9.5172Z"
                      fill="currentColor"
                    />
                    <path
                      fillRule="evenodd"
                      clipRule="evenodd"
                      d="M1.29266 2.7512C1.43005 2.36044 1.8582 2.15503 2.24896 2.29242L2.55036 2.39838C3.16689 2.61511 3.69052 2.79919 4.10261 3.00139C4.54324 3.21759 4.92109 3.48393 5.20527 3.89979C5.48725 4.31243 5.60367 4.76515 5.6574 5.26153C5.66124 5.29706 5.6648 5.33321 5.66809 5.36996L17.1203 5.36996C17.9389 5.36995 18.7735 5.36993 19.4606 5.44674C19.8103 5.48584 20.1569 5.54814 20.4634 5.65583C20.7639 5.76141 21.0942 5.93432 21.3292 6.23974C21.711 6.73613 21.7777 7.31414 21.7416 7.90034C21.7071 8.45845 21.5686 9.15234 21.4039 9.97723L21.3935 10.0295L21.3925 10.0341L20.8836 12.5033C20.7339 13.2298 20.6079 13.841 20.4455 14.3231C20.2731 14.8346 20.0341 15.2842 19.6076 15.6318C19.1811 15.9793 18.6925 16.1226 18.1568 16.1882C17.6518 16.25 17.0278 16.25 16.2862 16.25L10.8804 16.25C9.53464 16.25 8.44479 16.25 7.58656 16.1283C6.69032 16.0012 5.93752 15.7285 5.34366 15.1022C4.79742 14.526 4.50529 13.9144 4.35897 13.0601C4.22191 12.2598 4.20828 11.2125 4.20828 9.75996V7.03832C4.20828 6.29837 4.20726 5.80316 4.16611 5.42295C4.12678 5.0596 4.05708 4.87818 3.96682 4.74609C3.87876 4.61723 3.74509 4.4968 3.44186 4.34802C3.11902 4.18961 2.68026 4.03406 2.01266 3.79934L1.75145 3.7075C1.36068 3.57012 1.15527 3.14197 1.29266 2.7512Z"
                      fill="currentColor"
                    />
                  </svg>

                  <span className="absolute -right-1.5 -top-1.5 flex h-4.5 w-4.5 items-center justify-center rounded-full bg-blue text-[10px] font-medium text-white">
                    {product.length}
                  </span>
                </button>

                <button
                  id="Toggle"
                  aria-label="Toggler"
                  className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-3 text-dark transition hover:border-blue hover:text-blue"
                  onClick={() => setNavigationOpen(!navigationOpen)}
                >
                  <span className="block relative cursor-pointer w-5.5 h-5.5">
                    <span className="du-block absolute right-0 w-full h-full">
                      <span
                        className={`block relative top-0 left-0 bg-current rounded-sm w-0 h-0.5 my-1 ease-in-out duration-200 delay-[0] ${
                          !navigationOpen && "!w-full delay-300"
                        }`}
                      ></span>
                      <span
                        className={`block relative top-0 left-0 bg-current rounded-sm w-0 h-0.5 my-1 ease-in-out duration-200 delay-150 ${
                          !navigationOpen && "!w-full delay-400"
                        }`}
                      ></span>
                      <span
                        className={`block relative top-0 left-0 bg-current rounded-sm w-0 h-0.5 my-1 ease-in-out duration-200 delay-200 ${
                          !navigationOpen && "!w-full delay-500"
                        }`}
                      ></span>
                    </span>

                    <span className="block absolute right-0 w-full h-full rotate-45">
                      <span
                        className={`block bg-current rounded-sm ease-in-out duration-200 delay-300 absolute left-2.5 top-0 w-0.5 h-full ${
                          !navigationOpen && "!h-0 delay-[0] "
                        }`}
                      ></span>
                      <span
                        className={`block bg-current rounded-sm ease-in-out duration-200 delay-400 absolute left-0 top-2.5 w-full h-0.5 ${
                          !navigationOpen && "!h-0 dealy-200"
                        }`}
                      ></span>
                    </span>
                  </span>
                </button>
              </div>
            </div>

            <div className="w-full lg:max-w-[560px] xl:max-w-[620px] lg:justify-self-start">
              <form onSubmit={handleSearchSubmit}>
                <div className="relative min-w-0 w-full">
                  <input
                    onChange={(e) => setSearchQuery(e.target.value)}
                    value={searchQuery}
                    type="search"
                    name="search"
                    id="search"
                    placeholder={searchPlaceholder}
                    autoComplete="off"
                    onFocus={() => setSearchModalOpen(true)}
                    className="custom-search w-full rounded-[5px] bg-gray-1 border border-gray-3 py-2.5 pl-4 pr-10 outline-none ease-in duration-200 lg:min-w-[420px] xl:min-w-[520px]"
                  />

                  <button
                    type="submit"
                    id="search-btn"
                    aria-label="Search"
                    className="flex items-center justify-center absolute right-3 top-1/2 -translate-y-1/2 ease-in duration-200 hover:text-blue"
                  >
                    <svg
                      className="fill-current"
                      width="18"
                      height="18"
                      viewBox="0 0 18 18"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M17.2687 15.6656L12.6281 11.8969C14.5406 9.28123 14.3437 5.5406 11.9531 3.1781C10.6875 1.91248 8.99995 1.20935 7.19995 1.20935C5.39995 1.20935 3.71245 1.91248 2.44683 3.1781C-0.168799 5.79373 -0.168799 10.0687 2.44683 12.6844C3.71245 13.95 5.39995 14.6531 7.19995 14.6531C8.91558 14.6531 10.5187 14.0062 11.7843 12.8531L16.4812 16.65C16.5937 16.7344 16.7343 16.7906 16.875 16.7906C17.0718 16.7906 17.2406 16.7062 17.3531 16.5656C17.5781 16.2844 17.55 15.8906 17.2687 15.6656ZM7.19995 13.3875C5.73745 13.3875 4.38745 12.825 3.34683 11.7844C1.20933 9.64685 1.20933 6.18748 3.34683 4.0781C4.38745 3.03748 5.73745 2.47498 7.19995 2.47498C8.66245 2.47498 10.0125 3.03748 11.0531 4.0781C13.1906 6.2156 13.1906 9.67498 11.0531 11.7844C10.0406 12.825 8.66245 13.3875 7.19995 13.3875Z"
                        fill=""
                      />
                    </svg>
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* <!-- header top right --> */}
          <div className="flex w-full lg:w-auto items-center gap-5 xl:gap-6">
            {supportPhone ? <><div className="hidden xl:flex flex-col rounded-xl bg-gray-1 px-4 py-2.5">
              <span className="block text-2xs text-dark-4 uppercase">
                {supportLabel}
              </span>
              <p className="font-medium text-custom-sm text-dark">
                {supportPhone}
              </p>
            </div>

            {/* <!-- divider --> */}
            <span className="hidden xl:block w-px h-7.5 bg-gray-4"></span></> : null}

            <div className="hidden lg:flex w-full lg:w-auto justify-between items-center gap-5">
              <div className="flex items-center gap-5">
                <Link href={session ? "/account" : "/login"} className="flex items-center gap-2.5">
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      fillRule="evenodd"
                      clipRule="evenodd"
                      d="M12 1.25C9.37666 1.25 7.25001 3.37665 7.25001 6C7.25001 8.62335 9.37666 10.75 12 10.75C14.6234 10.75 16.75 8.62335 16.75 6C16.75 3.37665 14.6234 1.25 12 1.25ZM8.75001 6C8.75001 4.20507 10.2051 2.75 12 2.75C13.7949 2.75 15.25 4.20507 15.25 6C15.25 7.79493 13.7949 9.25 12 9.25C10.2051 9.25 8.75001 7.79493 8.75001 6Z"
                      fill="#3C50E0"
                    />
                    <path
                      fillRule="evenodd"
                      clipRule="evenodd"
                      d="M12 12.25C9.68646 12.25 7.55494 12.7759 5.97546 13.6643C4.4195 14.5396 3.25001 15.8661 3.25001 17.5L3.24995 17.602C3.24882 18.7638 3.2474 20.222 4.52642 21.2635C5.15589 21.7761 6.03649 22.1406 7.22622 22.3815C8.41927 22.6229 9.97424 22.75 12 22.75C14.0258 22.75 15.5808 22.6229 16.7738 22.3815C17.9635 22.1406 18.8441 21.7761 19.4736 21.2635C20.7526 20.222 20.7512 18.7638 20.7501 17.602L20.75 17.5C20.75 15.8661 19.5805 14.5396 18.0246 13.6643C16.4451 12.7759 14.3136 12.25 12 12.25ZM4.75001 17.5C4.75001 16.6487 5.37139 15.7251 6.71085 14.9717C8.02681 14.2315 9.89529 13.75 12 13.75C14.1047 13.75 15.9732 14.2315 17.2892 14.9717C18.6286 15.7251 19.25 16.6487 19.25 17.5C19.25 18.8078 19.2097 19.544 18.5264 20.1004C18.1559 20.4022 17.5365 20.6967 16.4762 20.9113C15.4193 21.1252 13.9742 21.25 12 21.25C10.0258 21.25 8.58075 21.1252 7.5238 20.9113C6.46354 20.6967 5.84413 20.4022 5.4736 20.1004C4.79033 19.544 4.75001 18.8078 4.75001 17.5Z"
                      fill="#3C50E0"
                    />
                  </svg>

                  <div>
                    <span className="block text-2xs text-dark-4 uppercase">
                      {accountHeading}
                    </span>
                    <p className="font-medium text-custom-sm text-dark">
                      {session ? (session.user.full_name || "Mi cuenta") : guestAccountLabel}
                    </p>
                  </div>
                </Link>

                {session ? (
                  <button
                    onClick={handleSignOut}
                    className="font-medium text-custom-sm text-dark ease-out duration-200 hover:text-blue"
                  >
                    {signOutLabel}
                  </button>
                ) : null}

                <button
                  onClick={handleOpenCartModal}
                  className="flex items-center gap-2.5"
                >
                  <span className="inline-block relative">
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M15.5433 9.5172C15.829 9.21725 15.8174 8.74252 15.5174 8.45686C15.2175 8.17119 14.7428 8.18277 14.4571 8.48272L12.1431 10.9125L11.5433 10.2827C11.2576 9.98277 10.7829 9.97119 10.483 10.2569C10.183 10.5425 10.1714 11.0173 10.4571 11.3172L11.6 12.5172C11.7415 12.6658 11.9378 12.75 12.1431 12.75C12.3483 12.75 12.5446 12.6658 12.6862 12.5172L15.5433 9.5172Z"
                        fill="#3C50E0"
                      />
                      <path
                        fillRule="evenodd"
                        clipRule="evenodd"
                        d="M1.29266 2.7512C1.43005 2.36044 1.8582 2.15503 2.24896 2.29242L2.55036 2.39838C3.16689 2.61511 3.69052 2.79919 4.10261 3.00139C4.54324 3.21759 4.92109 3.48393 5.20527 3.89979C5.48725 4.31243 5.60367 4.76515 5.6574 5.26153C5.66124 5.29706 5.6648 5.33321 5.66809 5.36996L17.1203 5.36996C17.9389 5.36995 18.7735 5.36993 19.4606 5.44674C19.8103 5.48584 20.1569 5.54814 20.4634 5.65583C20.7639 5.76141 21.0942 5.93432 21.3292 6.23974C21.711 6.73613 21.7777 7.31414 21.7416 7.90034C21.7071 8.45845 21.5686 9.15234 21.4039 9.97723L21.3935 10.0295L21.3925 10.0341L20.8836 12.5033C20.7339 13.2298 20.6079 13.841 20.4455 14.3231C20.2731 14.8346 20.0341 15.2842 19.6076 15.6318C19.1811 15.9793 18.6925 16.1226 18.1568 16.1882C17.6518 16.25 17.0278 16.25 16.2862 16.25L10.8804 16.25C9.53464 16.25 8.44479 16.25 7.58656 16.1283C6.69032 16.0012 5.93752 15.7285 5.34366 15.1022C4.79742 14.526 4.50529 13.9144 4.35897 13.0601C4.22191 12.2598 4.20828 11.2125 4.20828 9.75996V7.03832C4.20828 6.29837 4.20726 5.80316 4.16611 5.42295C4.12678 5.0596 4.05708 4.87818 3.96682 4.74609C3.87876 4.61723 3.74509 4.4968 3.44186 4.34802C3.11902 4.18961 2.68026 4.03406 2.01266 3.79934L1.75145 3.7075C1.36068 3.57012 1.15527 3.14197 1.29266 2.7512ZM5.70828 6.86996L5.70828 9.75996C5.70828 11.249 5.72628 12.1578 5.83744 12.8068C5.93933 13.4018 6.11202 13.7324 6.43219 14.0701C6.70473 14.3576 7.08235 14.5418 7.79716 14.6432C8.53783 14.7482 9.5209 14.75 10.9377 14.75H16.2406C17.0399 14.75 17.5714 14.7487 17.9746 14.6993C18.3573 14.6525 18.5348 14.571 18.66 14.469C18.7853 14.3669 18.9009 14.2095 19.024 13.8441C19.1537 13.4592 19.2623 12.9389 19.4237 12.156L19.9225 9.73591L19.9229 9.73369C20.1005 8.84376 20.217 8.2515 20.2444 7.80793C20.2704 7.38648 20.2043 7.23927 20.1429 7.15786C20.1367 7.15259 20.0931 7.11565 19.9661 7.07101C19.8107 7.01639 19.5895 6.97049 19.2939 6.93745C18.6991 6.87096 17.9454 6.86996 17.089 6.86996H5.70828Z"
                        fill="#3C50E0"
                      />
                      <path
                        fillRule="evenodd"
                        clipRule="evenodd"
                        d="M5.2502 19.5C5.2502 20.7426 6.25756 21.75 7.5002 21.75C8.74285 21.75 9.7502 20.7426 9.7502 19.5C9.7502 18.2573 8.74285 17.25 7.5002 17.25C6.25756 17.25 5.2502 18.2573 5.2502 19.5ZM7.5002 20.25C7.08599 20.25 6.7502 19.9142 6.7502 19.5C6.7502 19.0857 7.08599 18.75 7.5002 18.75C7.91442 18.75 8.2502 19.0857 8.2502 19.5C8.2502 19.9142 7.91442 20.25 7.5002 20.25Z"
                        fill="#3C50E0"
                      />
                      <path
                        fillRule="evenodd"
                        clipRule="evenodd"
                        d="M14.25 19.5001C14.25 20.7427 15.2574 21.7501 16.5 21.7501C17.7426 21.7501 18.75 20.7427 18.75 19.5001C18.75 18.2574 17.7426 17.2501 16.5 17.2501C15.2574 17.2501 14.25 18.2574 14.25 19.5001ZM16.5 20.2501C16.0858 20.2501 15.75 19.9143 15.75 19.5001C15.75 19.0859 16.0858 18.7501 16.5 18.7501C16.9142 18.7501 17.25 19.0859 17.25 19.5001C17.25 19.9143 16.9142 20.2501 16.5 20.2501Z"
                        fill="#3C50E0"
                      />
                    </svg>

                    <span className="flex items-center justify-center font-medium text-2xs absolute -right-2 -top-2.5 bg-blue w-4.5 h-4.5 rounded-full text-white">
                      {product.length}
                    </span>
                  </span>

                  <div>
                    <span className="block text-2xs text-dark-4 uppercase">
                      {cartHeading}
                    </span>
                    <p className="font-medium text-custom-sm text-dark">
                      {format(totalPrice)}
                    </p>
                  </div>
                </button>
              </div>

            </div>
          </div>
        </div>
        {/* <!-- header top end --> */}
      </div>

      <div className="border-t border-gray-3">
        <div className="max-w-[1170px] mx-auto px-4 sm:px-7.5 xl:px-0">
          <div className="flex items-center justify-between">
            {/* <!--=== Main Nav Start ===--> */}
            <div className="hidden xl:flex items-center justify-between">
              {/* <!-- Main Nav Start --> */}
              <nav>
                <ul className="flex xl:items-center flex-col xl:flex-row gap-5 xl:gap-6">
                  {menuItems.map((menuItem, i) =>
                    menuItem.submenu ? (
                      <Dropdown
                        key={i}
                        menuItem={menuItem}
                        stickyMenu={stickyMenu}
                      />
                    ) : (
                      <li
                        key={i}
                        className="group relative before:w-0 before:h-[3px] before:bg-blue before:absolute before:left-0 before:top-0 before:rounded-b-[3px] before:ease-out before:duration-200 hover:before:w-full "
                      >
                        <Link
                          href={menuItem.path}
                          className={`hover:text-blue text-custom-sm font-medium text-dark flex ${
                            stickyMenu ? "xl:py-4" : "xl:py-6"
                          }`}
                        >
                          {menuItem.title}
                        </Link>
                      </li>
                    )
                  )}
                </ul>
              </nav>
              {/* //   <!-- Main Nav End --> */}
            </div>
            {/* // <!--=== Main Nav End ===--> */}

            {/* // <!--=== Nav Right Start ===--> */}
            <div className="hidden xl:block">
              <ul className="flex items-center gap-5.5">
                <li className="py-4">
                  <a
                    href="#"
                    className="flex items-center gap-1.5 font-medium text-custom-sm text-dark hover:text-blue"
                  >
                    <svg
                      className="fill-current"
                      width="16"
                      height="16"
                      viewBox="0 0 16 16"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M2.45313 7.55556H1.70313V7.55556L2.45313 7.55556ZM2.45313 8.66667L1.92488 9.19908C2.21729 9.4892 2.68896 9.4892 2.98137 9.19908L2.45313 8.66667ZM4.10124 8.08797C4.39528 7.79623 4.39715 7.32135 4.10541 7.02731C3.81367 6.73327 3.3388 6.73141 3.04476 7.02315L4.10124 8.08797ZM1.86149 7.02315C1.56745 6.73141 1.09258 6.73327 0.800843 7.02731C0.509102 7.32135 0.510968 7.79623 0.805009 8.08797L1.86149 7.02315ZM12.1973 5.05946C12.4143 5.41232 12.8762 5.52252 13.229 5.30558C13.5819 5.08865 13.6921 4.62674 13.4752 4.27388L12.1973 5.05946ZM8.0525 1.25C4.5514 1.25 1.70313 4.06755 1.70313 7.55556H3.20313C3.20313 4.90706 5.3687 2.75 8.0525 2.75V1.25ZM1.70313 7.55556L1.70313 8.66667L3.20313 8.66667L3.20313 7.55556L1.70313 7.55556ZM2.98137 9.19908L4.10124 8.08797L3.04476 7.02315L1.92488 8.13426L2.98137 9.19908ZM2.98137 8.13426L1.86149 7.02315L0.805009 8.08797L1.92488 9.19908L2.98137 8.13426ZM13.4752 4.27388C12.3603 2.46049 10.3479 1.25 8.0525 1.25V2.75C9.80904 2.75 11.346 3.67466 12.1973 5.05946L13.4752 4.27388Z"
                        fill=""
                      />
                      <path
                        d="M13.5427 7.33337L14.0699 6.79996C13.7777 6.51118 13.3076 6.51118 13.0155 6.79996L13.5427 7.33337ZM11.8913 7.91107C11.5967 8.20225 11.5939 8.67711 11.8851 8.97171C12.1763 9.26631 12.6512 9.26908 12.9458 8.9779L11.8913 7.91107ZM14.1396 8.9779C14.4342 9.26908 14.9091 9.26631 15.2003 8.97171C15.4914 8.67711 15.4887 8.20225 15.1941 7.91107L14.1396 8.9779ZM3.75812 10.9395C3.54059 10.587 3.07849 10.4776 2.72599 10.6951C2.3735 10.9127 2.26409 11.3748 2.48163 11.7273L3.75812 10.9395ZM7.9219 14.75C11.4321 14.75 14.2927 11.9352 14.2927 8.44449H12.7927C12.7927 11.0903 10.6202 13.25 7.9219 13.25V14.75ZM14.2927 8.44449V7.33337H12.7927V8.44449H14.2927ZM13.0155 6.79996L11.8913 7.91107L12.9458 8.9779L14.0699 7.86679L13.0155 6.79996ZM13.0155 7.86679L14.1396 8.9779L15.1941 7.91107L14.0699 6.79996L13.0155 7.86679ZM2.48163 11.7273C3.60082 13.5408 5.62007 14.75 7.9219 14.75V13.25C6.15627 13.25 4.61261 12.3241 3.75812 10.9395L2.48163 11.7273Z"
                        fill=""
                      />
                    </svg>
                    {recentlyViewedLabel}
                  </a>
                </li>

                <li className="py-4">
                  <Link
                    href="/wishlist"
                    className="flex items-center gap-1.5 font-medium text-custom-sm text-dark hover:text-blue"
                  >
                    <svg
                      className="fill-current"
                      width="16"
                      height="16"
                      viewBox="0 0 16 16"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M5.97441 12.6073L6.43872 12.0183L5.97441 12.6073ZM7.99992 3.66709L7.45955 4.18719C7.60094 4.33408 7.79604 4.41709 7.99992 4.41709C8.2038 4.41709 8.3989 4.33408 8.54028 4.18719L7.99992 3.66709ZM10.0254 12.6073L10.4897 13.1962L10.0254 12.6073ZM6.43872 12.0183C5.41345 11.21 4.33627 10.4524 3.47904 9.48717C2.64752 8.55085 2.08325 7.47831 2.08325 6.0914H0.583252C0.583252 7.94644 1.3588 9.35867 2.35747 10.4832C3.33043 11.5788 4.57383 12.4582 5.51009 13.1962L6.43872 12.0183ZM2.08325 6.0914C2.08325 4.75102 2.84027 3.63995 3.85342 3.17683C4.81929 2.73533 6.15155 2.82823 7.45955 4.18719L8.54028 3.14699C6.84839 1.38917 4.84732 1.07324 3.22983 1.8126C1.65962 2.53035 0.583252 4.18982 0.583252 6.0914H2.08325ZM5.51009 13.1962C5.84928 13.4636 6.22932 13.7618 6.61834 13.9891C7.00711 14.2163 7.47619 14.4167 7.99992 14.4167V12.9167C7.85698 12.9167 7.65939 12.8601 7.37512 12.694C7.0911 12.5281 6.79171 12.2965 6.43872 12.0183L5.51009 13.1962ZM10.4897 13.1962C11.426 12.4582 12.6694 11.5788 13.6424 10.4832C14.641 9.35867 15.4166 7.94644 15.4166 6.0914H13.9166C13.9166 7.47831 13.3523 8.55085 12.5208 9.48717C11.6636 10.4524 10.5864 11.21 9.56112 12.0183L10.4897 13.1962ZM15.4166 6.0914C15.4166 4.18982 14.3402 2.53035 12.77 1.8126C11.1525 1.07324 9.15145 1.38917 7.45955 3.14699L8.54028 4.18719C9.84828 2.82823 11.1805 2.73533 12.1464 3.17683C13.1596 3.63995 13.9166 4.75102 13.9166 6.0914H15.4166ZM9.56112 12.0183C9.20813 12.2965 8.90874 12.5281 8.62471 12.694C8.34044 12.8601 8.14285 12.9167 7.99992 12.9167V14.4167C8.52365 14.4167 8.99273 14.2163 9.3815 13.9891C9.77052 13.7618 10.1506 13.4636 10.4897 13.1962L9.56112 12.0183Z"
                        fill=""
                      />
                    </svg>
                    {wishlistLabel}
                  </Link>
                </li>
              </ul>
            </div>
            {/* <!--=== Nav Right End ===--> */}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
