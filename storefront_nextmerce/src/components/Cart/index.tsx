"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Breadcrumb from "../Common/Breadcrumb";
import OrderSummary from "./OrderSummary";
import SingleItem from "./SingleItem";
import { useDispatch } from "react-redux";
import { AppDispatch, useAppSelector } from "@/redux/store";
import { removeAllItemsFromCart, type CartItem } from "@/redux/features/cart-slice";
import { isTrustedPreviewMessage } from "@/lib/preview";
import {
  cartTemplateContent,
  cartTemplateSection,
  normalizeCartTemplate,
  type CartTemplateDocument,
  type CartTemplateSection,
  type CartTemplateSectionType,
} from "@/lib/cart-template";

const previewCartItems: CartItem[] = [
  {
    id: 900001,
    title: "Producto de muestra",
    price: 89000,
    discountedPrice: 79000,
    quantity: 1,
    href: "/products",
    imgs: {
      thumbnails: ["/images/products/product-1-sm-1.png"],
      previews: ["/images/products/product-1-sm-1.png"],
    },
  },
  {
    id: 900002,
    title: "Producto destacado",
    price: 125000,
    discountedPrice: 109000,
    quantity: 2,
    href: "/products",
    imgs: {
      thumbnails: ["/images/products/product-2-sm-1.png"],
      previews: ["/images/products/product-2-sm-1.png"],
    },
  },
];

function settingBoolean(section: CartTemplateSection, key: string, fallback: boolean): boolean {
  return typeof section.settings[key] === "boolean" ? section.settings[key] as boolean : fallback;
}

function emptyCartIcon() {
  return (
    <svg className="mx-auto" width="88" height="88" viewBox="0 0 88 88" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="44" cy="44" r="44" fill="#F3F4F6" />
      <path d="M25.8 27.6C25.3 27.4 24.8 27.7 24.6 28.2C24.4 28.7 24.7 29.2 25.2 29.4L25.5 29.5C27.1 30 27.8 30.3 28.2 30.7C28.6 31 28.7 31.4 28.8 32.3C28.9 33.2 28.9 34.3 28.9 36V42.2C28.9 44.1 28.9 45.5 29.1 46.6C29.3 47.8 29.6 48.8 30.4 49.6C31.2 50.4 32.2 50.7 33.4 50.9C34.5 51.1 35.9 51.1 37.8 51.1H48.1C48.6 51.1 49 50.7 49 50.2C49 49.7 48.6 49.3 48.1 49.3H37.9C35.8 49.3 34.6 49.3 33.7 49.2C32.8 49 32.4 48.8 32 48.4C31.8 48.2 31.6 47.9 31.5 47.6H43.9C44.6 47.6 45.2 47.6 45.7 47.5C46.3 47.4 46.8 47.3 47.2 46.9C47.7 46.6 47.9 46.1 48.2 45.6C48.4 45.1 48.7 44.6 48.9 44L49.5 42.6C50 41.4 50.5 40.4 50.7 39.5C51 38.6 50.8 37.8 50.3 37.2C49.8 36.5 49 36.2 48.1 36.1C47.2 36 46.1 36 44.7 36H30.8C30.8 35.9 30.8 35.8 30.8 35.7C30.7 34.5 30.7 33.3 30.5 32.1C30.4 31.3 30.2 30.5 29.6 29.8C29 29.1 28.3 28.8 27.4 28.5L25.8 27.6Z" fill="#8D93A5" />
      <circle cx="33.9" cy="55.8" r="2.8" fill="#8D93A5" />
      <circle cx="45.1" cy="55.8" r="2.8" fill="#8D93A5" />
    </svg>
  );
}

const Cart = ({ cartTemplate = {} }: { cartTemplate?: CartTemplateDocument | Record<string, unknown> }) => {
  const cartItems = useAppSelector((state) => state.cartReducer.items);
  const dispatch = useDispatch<AppDispatch>();
  const [previewTemplate, setPreviewTemplate] = useState<unknown>(cartTemplate);
  const [previewMode, setPreviewMode] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedSectionId, setSelectedSectionId] = useState("");

  const normalizedTemplate = useMemo(() => normalizeCartTemplate(previewTemplate), [previewTemplate]);
  const content = useMemo(() => cartTemplateContent(normalizedTemplate), [normalizedTemplate]);
  const headerSection = useMemo(() => cartTemplateSection(normalizedTemplate, "cart_header"), [normalizedTemplate]);
  const itemsSection = useMemo(() => cartTemplateSection(normalizedTemplate, "cart_items"), [normalizedTemplate]);
  const summarySection = useMemo(() => cartTemplateSection(normalizedTemplate, "cart_summary"), [normalizedTemplate]);
  const emptySection = useMemo(() => cartTemplateSection(normalizedTemplate, "cart_empty"), [normalizedTemplate]);
  const hasRealItems = cartItems.length > 0;
  const displayedItems = previewMode && !hasRealItems ? previewCartItems : cartItems;
  const showFilledCart = displayedItems.length > 0;
  const showClearAction = settingBoolean(headerSection, "show_clear_action", true);
  const showVariant = settingBoolean(itemsSection, "show_variant", true);
  const showStockNotice = settingBoolean(itemsSection, "show_stock_notice", true);
  const showSummaryItems = settingBoolean(summarySection, "show_items", true);
  const showCheckoutButton = settingBoolean(summarySection, "show_checkout_button", true);
  const showContinueShopping = settingBoolean(emptySection, "show_continue_shopping", true);

  useEffect(() => {
    setPreviewTemplate(cartTemplate);
  }, [cartTemplate]);

  useEffect(() => {
    const handlePreviewMessage = (event: MessageEvent) => {
      if (!isTrustedPreviewMessage(event)) return;
      const message = event.data;
      if (!message || message.type !== "lumefy:preview:apply" || message.template !== "cart") return;

      setPreviewMode(true);
      if (message.document && typeof message.document === "object") setPreviewTemplate(message.document);
      if (typeof message.selectedSectionId === "string") setSelectedSectionId(message.selectedSectionId);
      if (typeof message.selectionMode === "boolean") setSelectionMode(message.selectionMode);
      window.parent.postMessage(
        { type: "lumefy:preview:ack", requestId: message.requestId || null },
        event.origin || "*",
      );
    };

    setPreviewMode(window.parent !== window);
    window.addEventListener("message", handlePreviewMessage);
    if (window.parent !== window) window.parent.postMessage({ type: "lumefy:preview:ready" }, "*");
    return () => window.removeEventListener("message", handlePreviewMessage);
  }, []);

  const handlePreviewSectionClick = (event: React.MouseEvent<HTMLElement>) => {
    if (!previewMode) return;
    const target = event.target as HTMLElement;
    const section = target.closest<HTMLElement>("[data-lumefy-cart-section]");
    if (!section) return;
    if (!selectionMode && target.closest("a,button,input,textarea,select")) return;
    const sectionId = section.dataset.lumefyCartSection;
    if (!sectionId) return;
    event.preventDefault();
    event.stopPropagation();
    setSelectedSectionId(sectionId);
    window.parent.postMessage({ type: "lumefy:preview:select", sectionId }, "*");
  };

  const sectionOrder = (type: CartTemplateSectionType) => {
    const index = normalizedTemplate.sections.findIndex((section) => section.type === type);
    return index < 0 ? 99 : index;
  };
  const sectionClass = (section: CartTemplateSection) => previewMode
    ? `lumefy-cart-preview-section ${selectedSectionId === section.id ? "lumefy-cart-preview-section--selected" : ""}`
    : "";

  return (
    <div className={previewMode && selectionMode ? "lumefy-preview--selecting" : undefined}>
      <section className="overflow-hidden bg-gray-2 pb-20 pt-5 lg:pt-16">
        <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
          <div className="cart-template-sections flex flex-col gap-7.5">
            <div
              className={sectionClass(headerSection)}
              data-lumefy-cart-section={previewMode ? "cart_header" : undefined}
              onClick={previewMode ? handlePreviewSectionClick : undefined}
              style={{ display: headerSection.enabled ? undefined : "none", order: sectionOrder("cart_header") }}
            >
              <Breadcrumb title={content.breadcrumb_title} pages={[content.breadcrumb_title]} />
              <div className="flex flex-wrap items-center justify-between gap-5 px-1 pt-7.5">
                <h2 className="font-medium text-dark text-2xl">{content.title}</h2>
                {showClearAction ? (
                  <button className="text-blue transition hover:text-blue-dark" onClick={() => { if (!previewMode) dispatch(removeAllItemsFromCart()); }}>
                    {content.clear_cart_label}
                  </button>
                ) : null}
              </div>
            </div>

            <div
              className={sectionClass(itemsSection)}
              data-lumefy-cart-section={previewMode ? "cart_items" : undefined}
              onClick={previewMode ? handlePreviewSectionClick : undefined}
              style={{ display: itemsSection.enabled && showFilledCart ? undefined : "none", order: sectionOrder("cart_items") }}
            >
              <div className="overflow-hidden rounded-[10px] bg-white shadow-1">
                <div className="w-full overflow-x-auto md:overflow-visible">
                  <div className="md:min-w-[1170px]">
                    <div className="hidden items-center px-7.5 py-5.5 md:flex">
                      <div className="min-w-[400px]"><p className="text-dark">{content.product_label}</p></div>
                      <div className="min-w-[180px]"><p className="text-dark">{content.price_label}</p></div>
                      <div className="min-w-[275px]"><p className="text-dark">{content.quantity_label}</p></div>
                      <div className="min-w-[200px]"><p className="text-dark">{content.subtotal_label}</p></div>
                      <div className="min-w-[50px]"><p className="text-dark text-right">{content.action_label}</p></div>
                    </div>
                    {displayedItems.map((item) => (
                      <SingleItem
                        item={item}
                        key={item.id}
                        content={content}
                        interactive={!previewMode}
                        showVariant={showVariant}
                        showStockNotice={showStockNotice}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div
              className={sectionClass(summarySection)}
              data-lumefy-cart-section={previewMode ? "cart_summary" : undefined}
              onClick={previewMode ? handlePreviewSectionClick : undefined}
              style={{ display: summarySection.enabled && showFilledCart ? undefined : "none", order: sectionOrder("cart_summary") }}
            >
              <div className="flex flex-col items-end lg:flex-row">
                <OrderSummary
                  previewItems={previewMode ? displayedItems : undefined}
                  content={content}
                  showItems={showSummaryItems}
                  showCheckoutButton={showCheckoutButton}
                />
              </div>
            </div>

            <div
              className={sectionClass(emptySection)}
              data-lumefy-cart-section={previewMode ? "cart_empty" : undefined}
              onClick={previewMode ? handlePreviewSectionClick : undefined}
              style={{ display: emptySection.enabled && (!hasRealItems || previewMode) ? undefined : "none", order: sectionOrder("cart_empty") }}
            >
              <div className="rounded-[10px] bg-white px-5 py-12 text-center shadow-1 sm:px-8">
                <div className="mx-auto pb-7.5">{emptyCartIcon()}</div>
                <p className="pb-2 text-xl font-medium text-dark">{content.empty_title}</p>
                <p className="pb-6 text-dark-3">{content.empty_description}</p>
                {showContinueShopping ? (
                  <Link href="/products" className="mx-auto flex w-full max-w-sm justify-center rounded-md bg-dark px-6 py-[13px] font-medium text-white ease-out duration-200 hover:bg-opacity-95">
                    {content.continue_shopping_label}
                  </Link>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Cart;
