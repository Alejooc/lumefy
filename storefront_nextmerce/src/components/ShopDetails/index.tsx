"use client";

import React, { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useDispatch } from "react-redux";

import Breadcrumb from "../Common/Breadcrumb";
import RecentlyViewdItems from "./RecentlyViewd";
import { usePreviewSlider } from "@/app/context/PreviewSliderContext";
import { Product, ProductVariant } from "@/types/product";
import { useStorefrontCurrency } from "@/lib/storefront-currency";
import { AppDispatch } from "@/redux/store";
import { addItemToCart } from "@/redux/features/cart-slice";
import { addItemToWishlist } from "@/redux/features/wishlist-slice";
import { updateproductDetails } from "@/redux/features/product-details";
import { useStorefrontAuth } from "@/lib/storefront-auth";
import { useStorefrontUi } from "@/lib/storefront-ui";
import { isTrustedPreviewMessage } from "@/lib/preview";
import {
  normalizeProductTemplate,
  productTemplateContent,
  productTemplateSection,
  productTemplateSectionEnabled,
  ProductTemplateDocument,
} from "@/lib/product-template";

function toSwatchColor(value: string): string {
  const normalized = value.trim().toLowerCase();
  const palette: Record<string, string> = {
    black: "#111827",
    negro: "#111827",
    white: "#f9fafb",
    blanco: "#f9fafb",
    blue: "#2563eb",
    azul: "#2563eb",
    red: "#dc2626",
    rojo: "#dc2626",
    green: "#16a34a",
    verde: "#16a34a",
    yellow: "#eab308",
    amarillo: "#eab308",
    pink: "#ec4899",
    rosado: "#ec4899",
    rosa: "#ec4899",
    purple: "#9333ea",
    morado: "#9333ea",
    orange: "#f97316",
    naranja: "#f97316",
    gray: "#6b7280",
    gris: "#6b7280",
    brown: "#92400e",
    cafe: "#92400e",
    beige: "#d6d3d1",
  };
  return palette[normalized] || "#9ca3af";
}

function stripHtml(value: string | undefined): string {
  return (value || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function normalizeFacetValue(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

function variantAttribute(variant: ProductVariant, keys: string[]): string {
  const attributes = variant.attributes || {};
  const normalizedAttributes = Object.entries(attributes).reduce<Record<string, unknown>>((result, [key, value]) => {
    result[normalizeFacetValue(key)] = value;
    return result;
  }, {});
  for (const key of keys) {
    const value = normalizedAttributes[normalizeFacetValue(key)];
    if (value !== undefined && String(value).trim()) return String(value).trim();
  }
  return "";
}

function looksLikeMeasure(value: string): boolean {
  const normalized = normalizeFacetValue(value);
  return Boolean(
      /\b(?:xs|s|m|l|xl|xxl|xxxl|2xl|3xl|4xl|5xl)\b/.test(normalized) ||
      /\b(?:doble|sencilla|queen|king|semidoble|individual|matrimonial|twin|full)\b/.test(normalized) ||
      /^\d+(?:[.,]\d+)?$/.test(normalized) ||
      /\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?/.test(normalized),
  );
}

function uniqueFacetValues(values: string[]): string[] {
  const seen = new Set<string>();
  return values
    .map((value) => value.trim())
    .filter((value) => {
      const normalized = normalizeFacetValue(value);
      if (!normalized || seen.has(normalized)) return false;
      seen.add(normalized);
      return true;
    });
}

function variantFacetOptions(
  variants: ProductVariant[] | undefined,
  providedValues: string[] | undefined,
  keys: string[],
  fallbackToMeasureName = false,
): string[] {
  const provided = uniqueFacetValues(providedValues || []);
  if (provided.length) return provided;

  const explicitValues = uniqueFacetValues(
    (variants || [])
      .map((variant) => variantAttribute(variant, keys))
      .filter(Boolean),
  );
  if (explicitValues.length) return explicitValues;

  if (!fallbackToMeasureName) return [];
  return uniqueFacetValues(
    (variants || [])
      .map((variant) => variant.name?.trim() || "")
      .filter((name) => name && looksLikeMeasure(name)),
  );
}

function numericVariantId(value: string): number {
  let hash = 0;
  for (const char of value) hash = (hash * 31 + char.charCodeAt(0)) | 0;
  return Math.abs(hash) || 1;
}

const ShopDetails = ({
  product,
  relatedItems,
  productTemplate,
}: {
  product: Product;
  relatedItems: Product[];
  productTemplate?: ProductTemplateDocument;
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const { format } = useStorefrontCurrency();
  const { openPreviewModal } = usePreviewSlider();
  const { session, loading: authLoading } = useStorefrontAuth();
  const { buttonLabels } = useStorefrontUi();
  const [previewTemplate, setPreviewTemplate] = useState<unknown>(productTemplate);
  const [previewMode, setPreviewMode] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedSectionId, setSelectedSectionId] = useState("");
  const [previewImg, setPreviewImg] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const normalizedProductTemplate = useMemo(
    () => normalizeProductTemplate(previewTemplate),
    [previewTemplate],
  );
  const content = productTemplateContent(previewTemplate);
  const gallerySection = productTemplateSection(previewTemplate, "product_gallery");
  const informationSection = productTemplateSection(previewTemplate, "product_information");
  const descriptionSection = productTemplateSection(previewTemplate, "product_description");
  const relatedSection = productTemplateSection(previewTemplate, "product_related");
  const galleryEnabled = productTemplateSectionEnabled(previewTemplate, "product_gallery");
  const informationEnabled = productTemplateSectionEnabled(previewTemplate, "product_information");
  const descriptionEnabled = productTemplateSectionEnabled(previewTemplate, "product_description");
  const relatedEnabled = productTemplateSectionEnabled(previewTemplate, "product_related");
  const productSectionOrder = (type: "product_gallery" | "product_information" | "product_description" | "product_related") => {
    const index = normalizedProductTemplate.sections.findIndex((section) => section.type === type);
    return index >= 0 ? index : 999;
  };
  const productPreviewClass = (sectionId: string) => previewMode
    ? `lumefy-product-preview-section ${selectedSectionId === sectionId ? "lumefy-product-preview-section--selected" : ""}`
    : "";
  const mainSectionOrder = Math.min(
    productSectionOrder("product_gallery"),
    productSectionOrder("product_information"),
  );

  useEffect(() => {
    setPreviewTemplate(productTemplate);
  }, [productTemplate]);

  useEffect(() => {
    const handlePreviewMessage = (event: MessageEvent) => {
      if (!isTrustedPreviewMessage(event)) return;
      const message = event.data;
      if (!message || message.type !== "lumefy:preview:apply" || message.template !== "product") return;
      setPreviewMode(true);
      if (message.document && typeof message.document === "object") {
        setPreviewTemplate(message.document as ProductTemplateDocument);
      }
      if (typeof message.selectedSectionId === "string") setSelectedSectionId(message.selectedSectionId);
      if (typeof message.selectionMode === "boolean") setSelectionMode(message.selectionMode);
      window.parent.postMessage(
        { type: "lumefy:preview:ack", requestId: message.requestId || null },
        event.origin || "*",
      );
    };

    setPreviewMode(window.parent !== window);
    window.addEventListener("message", handlePreviewMessage);
    if (window.parent !== window) {
      window.parent.postMessage({ type: "lumefy:preview:ready" }, "*");
    }
    return () => window.removeEventListener("message", handlePreviewMessage);
  }, []);

  const handlePreviewSectionClick = (event: React.MouseEvent<HTMLElement>) => {
    if (!previewMode) return;
    const target = event.target as HTMLElement;
    const section = target.closest<HTMLElement>("[data-lumefy-product-section]");
    if (!section) return;
    if (!selectionMode && target.closest("a,button,input,textarea,select")) return;
    const sectionId = section.dataset.lumefyProductSection;
    if (!sectionId) return;
    event.preventDefault();
    event.stopPropagation();
    setSelectedSectionId(sectionId);
    window.parent.postMessage({ type: "lumefy:preview:select", sectionId }, "*");
  };
  const sizeOptions = useMemo(
    () => variantFacetOptions(product.variants, product.availableSizes, ["size", "talla", "medida"], true),
    [product.availableSizes, product.variants],
  );
  const colorOptions = useMemo(
    () => variantFacetOptions(product.variants, product.availableColors, ["color", "colour", "colored"]),
    [product.availableColors, product.variants],
  );
  const [activeColor, setActiveColor] = useState(colorOptions[0] || "");
  const [activeSize, setActiveSize] = useState(sizeOptions[0] || "");
  const [activeTab, setActiveTab] = useState("description");

  const selectedVariant = useMemo(() => {
    const variants = product.variants || [];
    if (!variants.length) return undefined;
    const matches = (variant: ProductVariant, value: string, keys: string[]) => {
      if (!value) return true;
      const explicit = variantAttribute(variant, keys);
      return normalizeFacetValue(explicit || variant.name || "").includes(normalizeFacetValue(value));
    };
    const match = variants.find((variant) =>
      matches(variant, activeColor, ["color", "colour", "colored"]) &&
      matches(variant, activeSize, ["size", "talla", "medida"]),
    );
    return match || (!activeColor && !activeSize ? variants[0] : undefined);
  }, [activeColor, activeSize, product.variants]);
  const selectedVariantLabel = useMemo(() => {
    if (!selectedVariant) return "";
    const color = variantAttribute(selectedVariant, ["color", "colour", "colored"]);
    const size = variantAttribute(selectedVariant, ["size", "talla", "medida"]);
    return [color, size].filter(Boolean).join(" · ") || selectedVariant.name;
  }, [selectedVariant]);

  const previewImages = useMemo(() => {
    if (product.imgs?.previews?.length) {
      return product.imgs.previews;
    }
    if (product.imgs?.thumbnails?.length) {
      return product.imgs.thumbnails;
    }
    return ["/images/products/product-1-bg-1.png"];
  }, [product.imgs]);

  const thumbnailImages = product.imgs?.thumbnails?.length
    ? product.imgs.thumbnails
    : previewImages;

  const showBrand = informationSection.settings["show_brand"] !== false;
  const metadata = [
    showBrand && product.brandName ? { label: "Marca", value: product.brandName } : null,
    showBrand && product.categoryName ? { label: "Categoría", value: product.categoryName } : null,
    product.productType ? { label: "Tipo", value: product.productType } : null,
    sizeOptions.length
      ? { label: "Medidas", value: sizeOptions.join(", ") }
      : null,
    colorOptions.length
      ? { label: "Colores", value: colorOptions.join(", ") }
      : null,
  ].filter(Boolean) as Array<{ label: string; value: string }>;

  const displayedPrice = selectedVariant?.price ?? product.discountedPrice;
  const displayedComparePrice = selectedVariant?.compareAtPrice ?? product.price;
  const hasComparePrice = displayedComparePrice > displayedPrice;
  const isInStock = selectedVariant ? selectedVariant.inStock : product.inStock !== false;
  const stockQuantity = selectedVariant?.stockQuantity ?? product.stockQuantity;
  const stockLabel = !isInStock
    ? content.stock_out_label || buttonLabels.soldOut
    : stockQuantity !== undefined
      ? `${stockQuantity} disponibles`
      : content.stock_in_label || "Disponible";
  const descriptionText = stripHtml(product.description);

  const tabs = [
    { id: "description", title: content.description_tab_label, enabled: descriptionSection.settings["show_description_tab"] !== false },
    { id: "details", title: content.details_tab_label, enabled: descriptionSection.settings["show_details_tab"] !== false },
    { id: "reviews", title: content.reviews_tab_label, enabled: descriptionSection.settings["show_reviews_tab"] !== false },
  ].filter((tab) => tab.enabled);
  const activeContentTab = tabs.some((tab) => tab.id === activeTab) ? activeTab : tabs[0]?.id;

  const handleAddToCart = () => {
    if (!isInStock || (product.variants?.length && !selectedVariant)) return;
    dispatch(
      addItemToCart({
        ...product,
        id: selectedVariant ? numericVariantId(`${product.id}:${selectedVariant.id}`) : product.id,
        variantId: selectedVariant?.id,
        variantName: selectedVariantLabel,
        price: displayedComparePrice,
        discountedPrice: displayedPrice,
        inStock: isInStock,
        stockQuantity,
        quantity,
      }),
    );
  };

  const handleAddToWishlist = () => {
    if (!session) return;
    dispatch(
      addItemToWishlist({
        ...product,
        status: "available",
        quantity: 1,
      }),
    );
  };

  const handleOpenGallery = () => {
    dispatch(updateproductDetails(product));
    openPreviewModal();
  };

  return (
    <div className={previewMode && selectionMode ? "lumefy-preview--selecting" : undefined}>
      <Breadcrumb title={content.breadcrumb_title} pages={[content.breadcrumb_title]} headingLevel="h2" />

      {!product?.title ? (
        "Producto no disponible"
      ) : (
        <div className="product-template-sections">
          <section
            className="overflow-hidden relative pb-20 pt-5 lg:pt-20 xl:pt-28"
            onClick={previewMode ? handlePreviewSectionClick : undefined}
            style={{
              display: galleryEnabled || informationEnabled ? undefined : "none",
              order: mainSectionOrder,
            }}
          >
            <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
              <div className="flex flex-col lg:flex-row gap-7.5 xl:gap-17.5">
                <div
                  className={`lg:max-w-[570px] w-full ${productPreviewClass(gallerySection.id)}`}
                  data-lumefy-product-section={previewMode ? "product_gallery" : undefined}
                  style={{
                    display: galleryEnabled ? undefined : "none",
                    order: productSectionOrder("product_gallery"),
                  }}
                >
                  <div className="lumefy-product-gallery-main relative aspect-square w-full overflow-hidden rounded-lg shadow-1 bg-gray-2">
                    <button
                      onClick={handleOpenGallery}
                      aria-label="Ver todas las imágenes"
                      title="Ver todas las imágenes"
                      className="gallery__Image w-11 h-11 rounded-[5px] bg-gray-1 shadow-1 flex items-center justify-center ease-out duration-200 text-dark hover:text-blue absolute top-4 lg:top-6 right-4 lg:right-6 z-50"
                      style={{ display: gallerySection.settings["open_gallery"] === false ? "none" : undefined }}
                    >
                      <svg className="fill-current" width="22" height="22" viewBox="0 0 22 22" fill="none">
                        <path
                          fillRule="evenodd"
                          clipRule="evenodd"
                          d="M9.11493 1.14581L9.16665 1.14581C9.54634 1.14581 9.85415 1.45362 9.85415 1.83331C9.85415 2.21301 9.54634 2.52081 9.16665 2.52081C7.41873 2.52081 6.17695 2.52227 5.23492 2.64893C4.31268 2.77292 3.78133 3.00545 3.39339 3.39339C3.00545 3.78133 2.77292 4.31268 2.64893 5.23492C2.52227 6.17695 2.52081 7.41873 2.52081 9.16665C2.52081 9.54634 2.21301 9.85415 1.83331 9.85415C1.45362 9.85415 1.14581 9.54634 1.14581 9.16665L1.14581 9.11493C1.1458 7.43032 1.14579 6.09599 1.28619 5.05171C1.43068 3.97699 1.73512 3.10712 2.42112 2.42112C3.10712 1.73512 3.97699 1.43068 5.05171 1.28619C6.09599 1.14579 7.43032 1.1458 9.11493 1.14581ZM16.765 2.64893C15.823 2.52227 14.5812 2.52081 12.8333 2.52081C12.4536 2.52081 12.1458 2.21301 12.1458 1.83331C12.1458 1.45362 12.4536 1.14581 12.8333 1.14581L12.885 1.14581C14.5696 1.1458 15.904 1.14579 16.9483 1.28619C18.023 1.43068 18.8928 1.73512 19.5788 2.42112C20.2648 3.10712 20.5693 3.97699 20.7138 5.05171C20.8542 6.09599 20.8542 7.43032 20.8541 9.11494V9.16665C20.8541 9.54634 20.5463 9.85415 20.1666 9.85415C19.787 9.85415 19.4791 9.54634 19.4791 9.16665C19.4791 7.41873 19.4777 6.17695 19.351 5.23492C19.227 4.31268 18.9945 3.78133 18.6066 3.39339C18.2186 3.00545 17.6873 2.77292 16.765 2.64893Z"
                          fill=""
                        />
                      </svg>
                    </button>

                    <Image
                      src={previewImages[previewImg]}
                      alt={product.title}
                      width={570}
                      height={570}
                      sizes="(min-width: 1024px) 570px, 100vw"
                      className="block h-full w-full object-contain"
                    />
                  </div>

                  <div
                    className={`flex flex-wrap sm:flex-nowrap gap-4.5 mt-6 ${gallerySection.settings["gallery_layout"] === "grid" ? "lumefy-product-gallery-thumbnails--grid" : ""}`}
                    style={{ display: gallerySection.settings["show_thumbnails"] === false ? "none" : undefined }}
                  >
                    {thumbnailImages.map((item, key) => (
                      <button
                        onClick={() => setPreviewImg(key)}
                        key={`${item}-${key}`}
                        className={`flex items-center justify-center w-15 sm:w-25 h-15 sm:h-25 overflow-hidden rounded-lg bg-gray-2 shadow-1 ease-out duration-200 border-2 hover:border-blue ${
                          key === previewImg ? "border-blue" : "border-transparent"
                        }`}
                      >
                        <Image
                          width={100}
                          height={100}
                          src={item}
                          alt={`${product.title}-${key + 1}`}
                          className="block h-full w-full object-cover"
                          sizes="100px"
                        />
                      </button>
                    ))}
                  </div>
                </div>

                <div
                  className={`max-w-[539px] w-full ${productPreviewClass(informationSection.id)}`}
                  data-lumefy-product-section={previewMode ? "product_information" : undefined}
                  style={{
                    display: informationEnabled ? undefined : "none",
                    order: productSectionOrder("product_information"),
                  }}
                >
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <h1 className="font-semibold text-xl sm:text-2xl xl:text-custom-3 text-dark">
                      {product.title}
                    </h1>

                    {hasComparePrice && informationSection.settings["show_badge"] !== false ? (
                      <div className="inline-flex font-medium text-custom-sm text-white bg-blue rounded py-0.5 px-2.5">
                        {Math.round(((product.price - product.discountedPrice) / product.price) * 100)}% OFF
                      </div>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap items-center gap-5.5 mb-4.5">
                    <div className="flex items-center gap-2.5">
                      <span>{product.reviews ? `(${product.reviews} reseñas)` : "Reseñas próximamente"}</span>
                    </div>

                    {informationSection.settings["show_stock"] !== false ? <div className="flex items-center gap-1.5">
                      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                        <path
                          d="M10 0.5625C4.78125 0.5625 0.5625 4.78125 0.5625 10C0.5625 15.2188 4.78125 19.4688 10 19.4688C15.2188 19.4688 19.4688 15.2188 19.4688 10C19.4688 4.78125 15.2188 0.5625 10 0.5625ZM10 18.0625C5.5625 18.0625 1.96875 14.4375 1.96875 10C1.96875 5.5625 5.5625 1.96875 10 1.96875C14.4375 1.96875 18.0625 5.59375 18.0625 10.0312C18.0625 14.4375 14.4375 18.0625 10 18.0625Z"
                          fill="#22AD5C"
                        />
                      </svg>
                      <span className="text-green">{stockLabel}</span>
                    </div> : null}
                  </div>

                  <h3 className="font-medium text-custom-1 mb-4.5">
                    <span className="text-sm sm:text-base text-dark">
                      {content.price_label}: {format(displayedPrice)}
                    </span>
                    {hasComparePrice ? (
                        <span className="line-through"> {format(displayedComparePrice)} </span>
                    ) : null}
                  </h3>

                  <ul className="flex flex-col gap-2">
                    <li className="flex items-center gap-2.5">{content.free_delivery_text}</li>
                    <li className="flex items-center gap-2.5">{content.promo_text}</li>
                  </ul>

                  <div className="flex flex-col gap-4.5 border-y border-gray-3 mt-7.5 mb-9 py-9">
                    {colorOptions.length && informationSection.settings["show_variants"] !== false ? (
                      <div className="flex items-center gap-4">
                        <div className="min-w-[65px]">
                          <h4 className="font-medium text-dark">Color:</h4>
                        </div>

                        <div className="flex items-center gap-2.5">
                          {colorOptions.map((color) => (
                            <button
                              key={color}
                              type="button"
                              aria-label={color}
                              aria-pressed={activeColor === color}
                              onClick={() => setActiveColor(color)}
                              className={`flex items-center justify-center w-5.5 h-5.5 rounded-full ${
                                activeColor === color ? "border" : ""
                              }`}
                              style={{ borderColor: toSwatchColor(color) }}
                            >
                              <span className="block w-3 h-3 rounded-full" style={{ backgroundColor: toSwatchColor(color) }} />
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {sizeOptions.length && informationSection.settings["show_variants"] !== false ? (
                      <div className="flex items-start gap-4">
                        <div className="min-w-[65px] pt-2">
                          <h4 className="font-medium text-dark">Medida:</h4>
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                          {sizeOptions.map((size) => (
                            <button
                              key={size}
                              type="button"
                              aria-pressed={activeSize === size}
                              onClick={() => setActiveSize(size)}
                              className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                                activeSize === size
                                  ? "border-blue bg-blue text-white shadow-1"
                                  : "border-gray-3 bg-white text-dark hover:border-blue hover:text-blue"
                              }`}
                            >
                              {size}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  {selectedVariant?.sku && informationSection.settings["show_sku"] !== false ? (
                    <div className="mb-5 rounded-md bg-blue/5 px-4 py-3 text-sm text-dark">
                      <span className="font-medium">SKU:</span>{" "}
                      <strong>{selectedVariant.sku}</strong>
                    </div>
                  ) : null}

                  <div className="flex flex-wrap items-center gap-4.5">
                    {informationSection.settings["show_quantity"] !== false ? <div className="flex items-center rounded-md border border-gray-3">
                      <button
                        type="button"
                        aria-label="disminuir cantidad"
                        className="flex items-center justify-center w-12 h-12 ease-out duration-200 hover:text-blue"
                        onClick={() => quantity > 1 && setQuantity(quantity - 1)}
                      >
                        -
                      </button>
                      <span className="flex items-center justify-center w-16 h-12 border-x border-gray-4">
                        {quantity}
                      </span>
                      <button
                        type="button"
                        onClick={() => isInStock && (stockQuantity === undefined || quantity < stockQuantity) && setQuantity(quantity + 1)}
                        aria-label="aumentar cantidad"
                        className="flex items-center justify-center w-12 h-12 ease-out duration-200 hover:text-blue"
                      >
                        +
                      </button>
                    </div> : null}

                    <button
                      type="button"
                      onClick={handleAddToCart}
                      disabled={!isInStock || (Boolean(product.variants?.length) && !selectedVariant)}
                      className="inline-flex font-medium text-white bg-blue py-3 px-7 rounded-md ease-out duration-200 hover:bg-blue-dark disabled:cursor-not-allowed disabled:bg-gray-4"
                    >
                      {isInStock ? buttonLabels.addToCart : buttonLabels.soldOut}
                    </button>

                    {informationSection.settings["show_wishlist"] !== false ? <button
                      type="button"
                      onClick={handleAddToWishlist}
                      disabled={!session || authLoading}
                      title={session ? buttonLabels.addToWishlist : buttonLabels.loginToWishlist}
                      className="inline-flex items-center justify-center w-12 h-12 rounded-md border border-gray-3 ease-out duration-200 hover:text-white hover:bg-dark hover:border-transparent disabled:cursor-not-allowed disabled:opacity-50"
                      aria-label={session ? buttonLabels.addToWishlist : buttonLabels.loginToWishlist}
                    >
                      <svg className="fill-current" width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <path
                          fillRule="evenodd"
                          clipRule="evenodd"
                          d="M5.62436 4.42423C3.96537 5.18256 2.75 6.98626 2.75 9.13713C2.75 11.3345 3.64922 13.0283 4.93829 14.4798C6.00072 15.6761 7.28684 16.6677 8.54113 17.6346C8.83904 17.8643 9.13515 18.0926 9.42605 18.3219C9.95208 18.7366 10.4213 19.1006 10.8736 19.3649C11.3261 19.6293 11.6904 19.75 12 19.75C12.3096 19.75 12.6739 19.6293 13.1264 19.3649C13.5787 19.1006 14.0479 18.7366 14.574 18.3219C14.8649 18.0926 15.161 17.8643 15.4589 17.6346C16.7132 16.6677 17.9993 15.6761 19.0617 14.4798C20.3508 13.0283 21.25 11.3345 21.25 9.13713C21.25 6.98626 20.0346 5.18256 18.3756 4.42423C16.7639 3.68751 14.5983 3.88261 12.5404 6.02077C12.399 6.16766 12.2039 6.25067 12 6.25067C11.7961 6.25067 11.601 6.16766 11.4596 6.02077C9.40166 3.88261 7.23607 3.68751 5.62436 4.42423Z"
                          fill=""
                        />
                      </svg>
                    </button> : null}

                  </div>
                </div>
              </div>
            </div>
          </section>

          <section
            className={`overflow-hidden bg-gray-2 py-20 ${productPreviewClass(descriptionSection.id)}`}
            data-lumefy-product-section={previewMode ? "product_description" : undefined}
            onClick={previewMode ? handlePreviewSectionClick : undefined}
            style={{
              display: descriptionEnabled ? undefined : "none",
              order: productSectionOrder("product_description"),
            }}
          >
            <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
              <div className="flex flex-wrap items-center bg-white rounded-[10px] shadow-1 gap-5 xl:gap-12.5 py-4.5 px-4 sm:px-6">
                {tabs.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`font-medium lg:text-lg ease-out duration-200 hover:text-blue relative before:h-0.5 before:bg-blue before:absolute before:left-0 before:bottom-0 before:ease-out before:duration-200 hover:before:w-full ${
                      activeContentTab === item.id ? "text-blue before:w-full" : "text-dark before:w-0"
                    }`}
                  >
                    {item.title}
                  </button>
                ))}
              </div>

              <div className={activeContentTab === "description" ? "mt-12.5" : "hidden"}>
                <div className="rounded-xl bg-white shadow-1 p-4 sm:p-8">
                  <p className="text-dark">{descriptionText || "Este producto aún no tiene descripción detallada."}</p>
                </div>
              </div>

              <div className={activeContentTab === "details" ? "mt-10" : "hidden"}>
                <div className="rounded-xl bg-white shadow-1 p-4 sm:p-6">
                  {metadata.length ? (
                    metadata.map((item) => (
                      <div key={item.label} className="rounded-md even:bg-gray-1 flex py-4 px-4 sm:px-5">
                        <div className="max-w-[450px] min-w-[140px] w-full">
                          <p className="text-sm sm:text-base text-dark">{item.label}</p>
                        </div>
                        <div className="w-full">
                          <p className="text-sm sm:text-base text-dark">{item.value}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-md bg-gray-1 py-6 px-5 text-dark">
                      No hay informacion adicional disponible para este producto.
                    </div>
                  )}
                </div>
              </div>

              <div className={activeContentTab === "reviews" ? "mt-12.5" : "hidden"}>
                <div className="rounded-xl bg-white shadow-1 p-6 sm:p-8 text-center">
                  <h2 className="font-medium text-2xl text-dark mb-3">{content.reviews_empty_title}</h2>
                  <p className="mb-6 text-dark-3">{content.reviews_empty_description}</p>
                  <button
                    type="button"
                    className="inline-flex font-medium text-white bg-blue py-3 px-7 rounded-md ease-out duration-200 hover:bg-blue-dark"
                  >
                    {content.submit_review_label}
                  </button>
                </div>
              </div>
            </div>
          </section>

          {relatedEnabled ? (
            <div
              className={productPreviewClass(relatedSection.id)}
              data-lumefy-product-section={previewMode ? "product_related" : undefined}
              onClick={previewMode ? handlePreviewSectionClick : undefined}
              style={{ order: productSectionOrder("product_related") }}
            >
              <RecentlyViewdItems
                items={relatedItems}
                title={typeof relatedSection.settings["title"] === "string" ? relatedSection.settings["title"] : undefined}
                limit={Number(relatedSection.settings["count"] || 4)}
              />
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
};

export default ShopDetails;
