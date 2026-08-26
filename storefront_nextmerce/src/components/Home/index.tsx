"use client";

import React from "react";
import { useEffect, useState } from "react";
import Hero from "./Hero";
import Categories from "./Categories";
import NewArrival from "./NewArrivals";
import PromoBanner from "./PromoBanner";
import BestSeller from "./BestSeller";
import CounDown from "./Countdown";
import Testimonials from "./Testimonials";
import ClosingCta from "./ClosingCta";
import Newsletter from "../Common/Newsletter";

import { HomeLayoutSection, HomeLayoutSectionType, HomeViewModel } from "@/types/home";
import { storefrontImageUrl } from "@/lib/storefront-image";

const HOME_SECTION_TYPES = new Set<HomeLayoutSectionType>([
  "hero",
  "categories",
  "new_arrivals",
  "promo_banners",
  "best_sellers",
  "countdown",
  "testimonials",
  "newsletter",
  "closing_cta",
]);

function previewSections(value: unknown): HomeLayoutSection[] | null {
  if (!Array.isArray(value)) return null;
  const seen = new Set<string>();
  const sections = value
    .filter((section): section is Record<string, unknown> => Boolean(section) && typeof section === "object")
    .map((section, index) => {
      const type = typeof section["type"] === "string" ? section["type"] as HomeLayoutSectionType : null;
      const id = typeof section["id"] === "string" && section["id"] ? section["id"] : `preview-${index + 1}`;
      if (!type || !HOME_SECTION_TYPES.has(type) || seen.has(id)) return null;
      seen.add(id);
      return { id, type, enabled: section["enabled"] !== false, settings: previewObject(section["settings"]) };
    })
    .filter((section): section is HomeLayoutSection => Boolean(section));
  return sections.length ? sections : null;
}

function previewObject(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function previewText(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function previewStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? Array.from(new Set(value.filter((item): item is string => typeof item === "string" && Boolean(item.trim()))))
    : [];
}

function previewImage(value: unknown, fallback = ""): string {
  return storefrontImageUrl(previewText(value, fallback)) || fallback;
}

function previewParentOrigin(): string | null {
  if (typeof document === "undefined" || !document.referrer) return null;
  try {
    return new URL(document.referrer).origin;
  } catch {
    return null;
  }
}

function applyPreviewDocument(data: HomeViewModel, document: Record<string, unknown>): HomeViewModel {
  const home = previewObject(document["legacy_home"]);
  const next: HomeViewModel = {
    ...data,
    sections: previewSections(document["sections"]) || data.sections,
  };

  const categoryIds = previewStringList(
    next.sections.find((section) => section.type === "categories")?.settings?.["collection_ids"],
  );
  if (categoryIds.length) {
    const filteredCategories = data.categories.filter(
      (category) => category.sourceId && categoryIds.includes(category.sourceId),
    );
    if (filteredCategories.length) next.categories = filteredCategories;
  }
  const newArrivalIds = previewStringList(
    next.sections.find((section) => section.type === "new_arrivals")?.settings?.["product_ids"],
  );
  if (newArrivalIds.length) {
    const filteredProducts = data.newArrivals.filter(
      (product) => product.publishedProductId && newArrivalIds.includes(product.publishedProductId),
    );
    if (filteredProducts.length) next.newArrivals = filteredProducts;
  }
  const bestSellerIds = previewStringList(
    next.sections.find((section) => section.type === "best_sellers")?.settings?.["product_ids"],
  );
  if (bestSellerIds.length) {
    const filteredProducts = data.bestSellers.filter(
      (product) => product.publishedProductId && bestSellerIds.includes(product.publishedProductId),
    );
    if (filteredProducts.length) next.bestSellers = filteredProducts;
  }

  const heroSlides = Array.isArray(home["hero_slides"]) ? home["hero_slides"] : [];
  if (heroSlides.length) {
    next.heroSlides = heroSlides
      .filter((slide): slide is Record<string, unknown> => Boolean(slide) && typeof slide === "object")
      .map((slide, index) => ({
        ...(data.heroSlides[index] || data.heroSlides[0]),
        id: previewText(slide["id"], `preview-hero-${index + 1}`),
        title: previewText(slide["title"], data.heroSlides[index]?.title || "Nueva sección"),
        description: previewText(slide["description"], data.heroSlides[index]?.description || ""),
        ctaHref: previewText(slide["cta_href"], data.heroSlides[index]?.ctaHref || "/products"),
        image: previewImage(slide["image"], data.heroSlides[index]?.image || ""),
        overlayOpacity: Number(slide["overlay_opacity"] ?? data.heroSlides[index]?.overlayOpacity ?? 0.3),
        imagePosition: previewText(slide["image_position"], data.heroSlides[index]?.imagePosition || "center"),
        contentAlignment: slide["content_alignment"] === "center" ? "center" : "left",
        textColor: previewText(slide["text_color"], data.heroSlides[index]?.textColor || "#1C274C"),
        buttonLabel: previewText(slide["button_label"], data.heroSlides[index]?.buttonLabel || "Ver productos"),
        buttonColor: previewText(slide["button_color"], data.heroSlides[index]?.buttonColor || "#1C274C"),
      }));
  }

  const heroPromos = Array.isArray(home["hero_promos"]) ? home["hero_promos"] : [];
  if (heroPromos.length) {
    next.heroPromos = heroPromos
      .filter((promo): promo is Record<string, unknown> => Boolean(promo) && typeof promo === "object")
      .map((promo, index) => ({
        ...(data.heroPromos[index] || data.heroPromos[0]),
        id: previewText(promo["id"], `preview-promo-${index + 1}`),
        title: previewText(promo["title"], data.heroPromos[index]?.title || "Promoción"),
        offerLabel: previewText(promo["offer_label"], data.heroPromos[index]?.offerLabel || "Oferta especial"),
        href: previewText(promo["href"], data.heroPromos[index]?.href || "/products"),
        priceLabel: previewText(promo["price_label"], data.heroPromos[index]?.priceLabel || "Descubrir"),
        comparePriceLabel: previewText(promo["compare_price_label"], data.heroPromos[index]?.comparePriceLabel || ""),
        image: previewImage(promo["image"], data.heroPromos[index]?.image || ""),
        backgroundColor: previewText(promo["background_color"], data.heroPromos[index]?.backgroundColor || "#FFFFFF"),
        backgroundImageUrl: previewImage(promo["background_image_url"], data.heroPromos[index]?.backgroundImageUrl || ""),
      }));
  }

  const promoBanners = Array.isArray(home["promo_banners"]) ? home["promo_banners"] : [];
  if (promoBanners.length) {
    next.promoBanners = promoBanners
      .filter((banner): banner is Record<string, unknown> => Boolean(banner) && typeof banner === "object")
      .map((banner, index) => ({
        ...(data.promoBanners[index] || data.promoBanners[0]),
        id: previewText(banner["id"], data.promoBanners[index]?.id || `preview-promo-${index + 1}`),
        title: previewText(banner["title"], data.promoBanners[index]?.title || "Campaña"),
        subtitle: previewText(banner["subtitle"], data.promoBanners[index]?.subtitle || ""),
        description: previewText(banner["description"], data.promoBanners[index]?.description || ""),
        ctaLabel: previewText(banner["cta_label"], data.promoBanners[index]?.ctaLabel || "Ver productos"),
        ctaHref: previewText(banner["cta_href"], data.promoBanners[index]?.ctaHref || "/products"),
        image: previewImage(banner["image_url"], data.promoBanners[index]?.image || ""),
        backgroundColor: previewText(banner["background_color"], data.promoBanners[index]?.backgroundColor || ""),
        accentColor: previewText(banner["accent_color"], data.promoBanners[index]?.accentColor || ""),
      }));
  }

  const categorySection = previewObject(home["category_section"]);
  const newArrivalsSection = previewObject(home["new_arrivals_section"]);
  const bestSellersSection = previewObject(home["best_sellers_section"]);
  next.categorySection = {
    ...data.categorySection,
    eyebrow: previewText(categorySection["eyebrow"], data.categorySection.eyebrow || "Explora"),
    title: previewText(categorySection["title"], data.categorySection.title),
  };
  next.newArrivalsSection = {
    ...data.newArrivalsSection,
    eyebrow: previewText(newArrivalsSection["eyebrow"], data.newArrivalsSection.eyebrow || "Recién llegados"),
    title: previewText(newArrivalsSection["title"], data.newArrivalsSection.title),
    ctaLabel: previewText(newArrivalsSection["cta_label"], data.newArrivalsSection.ctaLabel || "Ver todos"),
    ctaHref: previewText(newArrivalsSection["cta_href"], data.newArrivalsSection.ctaHref || "/products"),
  };
  next.bestSellersSection = {
    ...data.bestSellersSection,
    eyebrow: previewText(bestSellersSection["eyebrow"], data.bestSellersSection.eyebrow || "Lo más elegido"),
    title: previewText(bestSellersSection["title"], data.bestSellersSection.title),
    ctaLabel: previewText(bestSellersSection["cta_label"], data.bestSellersSection.ctaLabel || "Ver todos"),
    ctaHref: previewText(bestSellersSection["cta_href"], data.bestSellersSection.ctaHref || "/products"),
  };

  const countdown = previewObject(home["countdown"]);
  const newsletter = previewObject(home["newsletter"]);
  next.countdown = {
    ...data.countdown,
    enabled: countdown["enabled"] !== false,
    eyebrow: previewText(countdown["eyebrow"], data.countdown.eyebrow || "Oferta especial"),
    title: previewText(countdown["title"], data.countdown.title),
    description: previewText(countdown["description"], data.countdown.description || ""),
    ctaLabel: previewText(countdown["cta_label"], data.countdown.ctaLabel || "Ver oferta"),
    ctaHref: previewText(countdown["cta_href"], data.countdown.ctaHref || "/products"),
    deadline: previewText(countdown["deadline"], data.countdown.deadline || ""),
    backgroundColor: previewText(countdown["background_color"], data.countdown.backgroundColor || "#D0E9F3"),
    backgroundImageUrl: previewImage(countdown["background_image_url"], data.countdown.backgroundImageUrl || ""),
    productImageUrl: previewImage(countdown["product_image_url"], data.countdown.productImageUrl || ""),
  };
  next.newsletter = {
    ...data.newsletter,
    enabled: newsletter["enabled"] !== false,
    title: previewText(newsletter["title"], data.newsletter.title),
    description: previewText(newsletter["description"], data.newsletter.description || ""),
    placeholder: previewText(newsletter["placeholder"], data.newsletter.placeholder || "Tu correo electrónico"),
    buttonLabel: previewText(newsletter["button_label"], data.newsletter.buttonLabel || "Registrarme"),
    backgroundImageUrl: previewImage(newsletter["background_image_url"], data.newsletter.backgroundImageUrl || ""),
  };

  const testimonials = previewObject(home["testimonials"]);
  next.testimonialsSection = {
    ...data.testimonialsSection,
    enabled: testimonials["enabled"] !== false,
    eyebrow: previewText(testimonials["eyebrow"], data.testimonialsSection.eyebrow || "Testimonios"),
    title: previewText(testimonials["title"], data.testimonialsSection.title),
  };
  const testimonialItems = Array.isArray(testimonials["items"]) ? testimonials["items"] : [];
  if (testimonialItems.length) {
    next.testimonials = testimonialItems
      .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
      .map((item, index) => ({
        ...(data.testimonials[index] || data.testimonials[0]),
        review: previewText(item["review"], data.testimonials[index]?.review || ""),
        authorName: previewText(item["author_name"], data.testimonials[index]?.authorName || "Cliente"),
        authorRole: previewText(item["author_role"], data.testimonials[index]?.authorRole || ""),
        authorImg: previewImage(item["author_image"], data.testimonials[index]?.authorImg || "/images/users/user-01.jpg"),
      }))
      .filter((item) => item.review && item.authorName);
  }

  return next;
}

function renderSection(
  section: HomeLayoutSection,
  data: HomeViewModel,
  onSelect?: (sectionId: string) => void,
) {
  if (!section.enabled) return null;
  let rendered: React.ReactNode;
  switch (section.type) {
    case "hero":
      rendered = <Hero slides={data.heroSlides} promos={data.heroPromos} features={data.features} />;
      break;
    case "categories":
      rendered = <Categories items={data.categories} section={data.categorySection} />;
      break;
    case "new_arrivals":
      rendered = <NewArrival items={data.newArrivals} section={data.newArrivalsSection} />;
      break;
    case "promo_banners":
      rendered = <PromoBanner items={data.promoBanners} />;
      break;
    case "best_sellers":
      rendered = <BestSeller items={data.bestSellers} section={data.bestSellersSection} />;
      break;
    case "countdown":
      rendered = <CounDown content={data.countdown} />;
      break;
    case "testimonials":
      rendered = <Testimonials section={data.testimonialsSection} items={data.testimonials} />;
      break;
    case "newsletter":
      rendered = <Newsletter storefrontId={data.storefrontId} content={data.newsletter} />;
      break;
    case "closing_cta":
      rendered = <ClosingCta storeName={data.storeName} />;
      break;
    default:
      return null;
  }

  if (!onSelect) return rendered;
  return (
    <div
      className="lumefy-preview-section"
      data-lumefy-preview-section={section.id}
      onClick={(event) => {
        if ((event.target as HTMLElement).closest("a,button,input,textarea,select")) return;
        event.stopPropagation();
        onSelect(section.id);
      }}
    >
      {rendered}
    </div>
  );
}

const Home = ({ data }: { data: HomeViewModel }) => {
  const [previewData, setPreviewData] = useState(data);
  const [previewMode, setPreviewMode] = useState(false);
  const [parentOrigin, setParentOrigin] = useState<string | null>(null);

  useEffect(() => {
    const expectedParentOrigin = previewParentOrigin();
    setPreviewMode(window.parent !== window);
    setParentOrigin(expectedParentOrigin);
    const handlePreviewMessage = (event: MessageEvent) => {
      if (event.source !== window.parent) return;
      if (expectedParentOrigin && event.origin !== expectedParentOrigin) return;
      const message = event.data;
      if (!message || message.type !== "lumefy:preview:apply" || message.template !== "home") return;
      if (message.document && typeof message.document === "object") {
        setPreviewData(applyPreviewDocument(data, message.document as Record<string, unknown>));
      }
      window.parent.postMessage(
        { type: "lumefy:preview:ack", requestId: message.requestId || null },
        expectedParentOrigin || event.origin || "*",
      );
    };

    window.addEventListener("message", handlePreviewMessage);
    if (window.parent !== window) {
      window.parent.postMessage({ type: "lumefy:preview:ready" }, expectedParentOrigin || "*");
    }
    return () => window.removeEventListener("message", handlePreviewMessage);
  }, [data]);

  return (
    <main>
      {previewData.sections.map((section) => (
        <React.Fragment key={section.id}>
          {renderSection(
            section,
            previewData,
            previewMode
              ? (sectionId) => window.parent.postMessage(
                  { type: "lumefy:preview:select", sectionId },
                  parentOrigin || "*",
                )
              : undefined,
          )}
        </React.Fragment>
      ))}
    </main>
  );
};

export default Home;
