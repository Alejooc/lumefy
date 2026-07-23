import { Category } from "@/types/category";
import { HomeViewModel } from "@/types/home";
import { Product } from "@/types/product";
import { Testimonial } from "@/types/testimonial";
import { PublicCollection, PublicProduct } from "@/types/storefront";
import { getStorefrontBranding } from "./storefront-branding";
import { storefrontImageUrl } from "./storefront-image";

import {
  getPublicCollectionBySlug,
  getPublicCollections,
  resolveStorefront,
} from "./storefront-api";

function numericId(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) | 0;
  }
  return Math.abs(hash) || 1;
}

function moneyLabel(currency: string, value: number | null | undefined): string {
  if (value == null) {
    return "";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function fallbackImage(seed: string): string {
  return `/images/products/product-${(numericId(seed) % 8) + 1}-bg-1.png`;
}

function toTemplateProduct(product: PublicProduct): Product {
  const previewImage = storefrontImageUrl(product.image_url) || storefrontImageUrl(product.gallery[0]) || fallbackImage(product.slug);
  const secondaryImage = storefrontImageUrl(product.gallery[1]) || storefrontImageUrl(product.image_url) || fallbackImage(`${product.slug}-alt`);
  const compare = product.compare_at_price ?? product.base_price ?? product.price;

  return {
    id: numericId(product.id),
    publishedProductId: product.id,
    title: product.title,
    description: product.description || "",
    reviews: product.is_featured ? 24 : 12,
    price: Number(compare || product.price),
    discountedPrice: Number(product.price),
    href: `/products/${encodeURIComponent(product.slug)}`,
    slug: product.slug,
    inStock: product.in_stock,
    stockQuantity: product.stock_quantity ?? undefined,
    imgs: {
      thumbnails: [previewImage, secondaryImage],
      previews: [previewImage, secondaryImage],
    },
  };
}

function toTemplateCategory(collection: PublicCollection): Category {
  return {
    id: numericId(collection.id),
    title: collection.name,
    img: storefrontImageUrl(collection.image_url) || fallbackImage(collection.slug),
    href: `/products?collection=${encodeURIComponent(collection.slug)}`,
    backgroundColor: "#F2F3F8",
    overlayOpacity: 0.18,
    imagePosition: "center",
  };
}

function homeSettings(storefront: { theme_settings?: Record<string, unknown> | null }): Record<string, unknown> {
  const themeSettings = storefront.theme_settings;
  if (!themeSettings || typeof themeSettings !== "object") {
    return {};
  }
  const home = themeSettings["home"];
  return home && typeof home === "object" ? (home as Record<string, unknown>) : {};
}

function stringOrUndefined(value: unknown): string | undefined {
  const text = typeof value === "string" ? value.trim() : "";
  return text || undefined;
}

function booleanOrDefault(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function objectOrEmpty(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function arrayOfObjects(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    : [];
}

function defaultHomeFeatures() {
  return [
    {
      id: "feature-1",
      title: "Envíos confiables",
      description: "Consulta las condiciones de entrega",
      image: "/images/icons/icon-01.svg",
    },
    {
      id: "feature-2",
      title: "Cambios y devoluciones",
      description: "Compra con tranquilidad",
      image: "/images/icons/icon-02.svg",
    },
    {
      id: "feature-3",
      title: "Pagos seguros",
      description: "Tus datos siempre protegidos",
      image: "/images/icons/icon-03.svg",
    },
    {
      id: "feature-4",
      title: "Atención al cliente",
      description: "Estamos para ayudarte",
      image: "/images/icons/icon-04.svg",
    },
  ];
}

function defaultTestimonials(): Testimonial[] {
  return [];
}

export async function loadHomeViewModel(): Promise<HomeViewModel> {
  const storefront = await resolveStorefront();
  const branding = getStorefrontBranding(storefront);
  const home = homeSettings(storefront);
  const collections = await getPublicCollections(storefront.id);
  const categoryFallbackItems = collections.map(toTemplateCategory);

  const detailedCollections = await Promise.all(
    collections.slice(0, 6).map(async (collection) => {
      try {
        return await getPublicCollectionBySlug(storefront.id, collection.slug);
      } catch {
        return collection;
      }
    }),
  );

  const collectionProducts = detailedCollections.flatMap((collection) => collection.products || []);
  const uniqueProducts = Array.from(new Map(collectionProducts.map((product) => [product.id, product])).values());
  const featuredProducts = uniqueProducts.filter((product) => product.is_featured);
  const sortedProducts = (featuredProducts.length ? featuredProducts : uniqueProducts).slice();
  const configuredHeroSlides = arrayOfObjects(home["hero_slides"]);
  const configuredHeroPromos = arrayOfObjects(home["hero_promos"]);
  const categorySection = objectOrEmpty(home["category_section"]);
  const configuredCategoryCards = arrayOfObjects(home["category_cards"]);
  const newArrivalsSection = objectOrEmpty(home["new_arrivals_section"]);
  const bestSellersSection = objectOrEmpty(home["best_sellers_section"]);
  const configuredFeatures = arrayOfObjects(home["features"]);
  const countdown = objectOrEmpty(home["countdown"]);
  const newsletter = objectOrEmpty(home["newsletter"]);
  const testimonials = objectOrEmpty(home["testimonials"]);

  const fallbackHeroSlides = sortedProducts.slice(0, 2).map((product, index) => {
    return {
      id: product.id,
      title: product.title,
      description: product.description || `Conoce ${product.title} en la tienda online de ${storefront.name}.`,
      ctaHref: `/products/${encodeURIComponent(product.slug)}`,
      image: storefrontImageUrl(product.image_url) || storefrontImageUrl(product.gallery[0]) || fallbackImage(product.slug),
      overlayOpacity: 0.72,
      imagePosition: "center",
      contentAlignment: "left" as const,
      textColor: "#1C274C",
      buttonLabel: "Ver producto",
      buttonColor: "#1C274C",
    };
  });

  const fallbackHeroPromos = detailedCollections.slice(0, 2).map((collection, index) => {
    const sourceProduct = collection.products?.[0] || sortedProducts[index];
    const compare = sourceProduct?.compare_at_price ?? sourceProduct?.base_price ?? null;
    return {
      id: collection.id,
      title: collection.name,
      offerLabel: "Oferta especial",
      href: `/products?collection=${encodeURIComponent(collection.slug)}`,
      priceLabel: sourceProduct ? moneyLabel(storefront.currency, sourceProduct.price) : "Nuevo",
      comparePriceLabel: compare && sourceProduct && compare > sourceProduct.price ? moneyLabel(storefront.currency, compare) : undefined,
      image:
        storefrontImageUrl(collection.image_url) ||
        storefrontImageUrl(sourceProduct?.image_url) ||
        storefrontImageUrl(sourceProduct?.gallery?.[0]) ||
        fallbackImage(collection.slug),
      backgroundColor: "#FFFFFF",
      backgroundImageUrl: undefined,
    };
  });

  const heroSlides = configuredHeroSlides.length
    ? configuredHeroSlides
        .map((slide, index) => ({
          id: String(slide["id"] || `hero-slide-${index + 1}`),
          title: stringOrUndefined(slide["title"]) || "",
          description: stringOrUndefined(slide["description"]) || "",
          ctaHref: stringOrUndefined(slide["cta_href"]) || "/products",
          image: storefrontImageUrl(stringOrUndefined(slide["image"])) || fallbackImage(`hero-${index + 1}`),
          overlayOpacity: Number(slide["overlay_opacity"] ?? 0.72),
          imagePosition: stringOrUndefined(slide["image_position"]) || "center",
          contentAlignment: stringOrUndefined(slide["content_alignment"]) === "center" ? "center" as const : "left" as const,
          textColor: stringOrUndefined(slide["text_color"]) || "#1C274C",
          buttonLabel: stringOrUndefined(slide["button_label"]) || "Ver productos",
          buttonColor: stringOrUndefined(slide["button_color"]) || "#1C274C",
        }))
        .filter((slide) => slide.title)
    : fallbackHeroSlides;

  const heroPromos = configuredHeroPromos.length
    ? configuredHeroPromos
        .map((promo, index) => ({
          id: String(promo["id"] || `hero-promo-${index + 1}`),
          title: stringOrUndefined(promo["title"]) || "",
          offerLabel: stringOrUndefined(promo["offer_label"]) || "Oferta especial",
          href: stringOrUndefined(promo["href"]) || "/products",
          priceLabel: stringOrUndefined(promo["price_label"]) || "Nuevo",
          comparePriceLabel: stringOrUndefined(promo["compare_price_label"]),
          image: storefrontImageUrl(stringOrUndefined(promo["image"])) || fallbackImage(`hero-promo-${index + 1}`),
          backgroundColor: stringOrUndefined(promo["background_color"]) || "#FFFFFF",
          backgroundImageUrl: storefrontImageUrl(stringOrUndefined(promo["background_image_url"])),
        }))
        .filter((promo) => promo.title)
    : fallbackHeroPromos;

  const configuredPromoBanners = arrayOfObjects(home["promo_banners"]);
  const features = configuredFeatures.length
    ? configuredFeatures
        .map((feature, index) => ({
          id: String(feature["id"] || `feature-${index + 1}`),
          title: stringOrUndefined(feature["title"]) || "",
          description: stringOrUndefined(feature["description"]) || "",
          image: storefrontImageUrl(stringOrUndefined(feature["image"])) || `/images/icons/icon-0${(index % 4) + 1}.svg`,
        }))
        .filter((feature) => feature.title)
    : defaultHomeFeatures();
  const configuredTestimonials = arrayOfObjects(testimonials["items"]);
  const testimonialItems = configuredTestimonials.length
    ? configuredTestimonials
        .map((item) => ({
          review: stringOrUndefined(item["review"]) || "",
          authorName: stringOrUndefined(item["author_name"]) || "",
          authorRole: stringOrUndefined(item["author_role"]) || "",
          authorImg: stringOrUndefined(item["author_image"]) || "/images/users/user-01.jpg",
        }))
        .filter((item) => item.review && item.authorName)
    : defaultTestimonials();
  const promoBanners = configuredPromoBanners.length
    ? configuredPromoBanners.slice(0, 3).map((banner, index) => ({
        id: String(banner["id"] || `promo-${index + 1}`),
        title: stringOrUndefined(banner["title"]) || "",
        subtitle: stringOrUndefined(banner["subtitle"]),
        description: stringOrUndefined(banner["description"]),
        ctaLabel: stringOrUndefined(banner["cta_label"]) || "Ver productos",
        ctaHref: stringOrUndefined(banner["cta_href"]) || "/products",
        image: storefrontImageUrl(stringOrUndefined(banner["image_url"])),
        backgroundColor: stringOrUndefined(banner["background_color"]),
        accentColor: stringOrUndefined(banner["accent_color"]),
      })).filter((banner) => banner.title)
    : branding.promoBanners.length
    ? branding.promoBanners.slice(0, 3).map((banner) => ({
        id: banner.id,
        title: banner.title,
        subtitle: banner.subtitle || undefined,
        description: banner.description || undefined,
        ctaLabel: banner.cta_label?.trim() || "Ver productos",
        ctaHref: banner.cta_href?.trim() || "#",
        image: storefrontImageUrl(banner.image_url),
        backgroundColor: banner.background_color?.trim() || undefined,
        accentColor: banner.accent_color?.trim() || undefined,
      }))
    : [];

  return {
      storeName: storefront.name,
      currency: storefront.currency,
      heroSlides,
      heroPromos,
      features,
      promoBanners,
      categorySection: {
        eyebrow: stringOrUndefined(categorySection["eyebrow"]) || "Explora",
        title: stringOrUndefined(categorySection["title"]) || "Compra por categoría",
      },
      categories: configuredCategoryCards.length
        ? configuredCategoryCards
            .map((card, index) => ({
              id: numericId(String(card["id"] || `category-card-${index + 1}`)),
              title: stringOrUndefined(card["title"]) || "",
              img: storefrontImageUrl(stringOrUndefined(card["image"])) || fallbackImage(`category-card-${index + 1}`),
              href: stringOrUndefined(card["href"]) || "/products",
              backgroundColor: stringOrUndefined(card["background_color"]) || "#F2F3F8",
              overlayOpacity: Number(card["overlay_opacity"] ?? 0.18),
              imagePosition: stringOrUndefined(card["image_position"]) || "center",
            }))
            .filter((card) => card.title)
        : categoryFallbackItems,
      newArrivalsSection: {
        eyebrow: stringOrUndefined(newArrivalsSection["eyebrow"]) || "Recién llegados",
        title: stringOrUndefined(newArrivalsSection["title"]) || "Novedades",
        ctaLabel: stringOrUndefined(newArrivalsSection["cta_label"]) || "Ver todos",
        ctaHref: stringOrUndefined(newArrivalsSection["cta_href"]) || "/products",
      },
      newArrivals: uniqueProducts.slice(0, 8).map(toTemplateProduct),
      bestSellersSection: {
        eyebrow: stringOrUndefined(bestSellersSection["eyebrow"]) || "Lo más elegido",
        title: stringOrUndefined(bestSellersSection["title"]) || "Productos destacados",
        ctaLabel: stringOrUndefined(bestSellersSection["cta_label"]) || "Ver todos",
        ctaHref: stringOrUndefined(bestSellersSection["cta_href"]) || "/products",
      },
      bestSellers: (featuredProducts.length ? featuredProducts : uniqueProducts).slice(0, 6).map(toTemplateProduct),
      countdown: {
        enabled: booleanOrDefault(countdown["enabled"], false),
        eyebrow: stringOrUndefined(countdown["eyebrow"]) || "Oferta especial",
        title: stringOrUndefined(countdown["title"]) || "No te pierdas esta oportunidad",
        description: stringOrUndefined(countdown["description"]) || "Descubre productos seleccionados para ti.",
        ctaLabel: stringOrUndefined(countdown["cta_label"]) || "Ver oferta",
        ctaHref: stringOrUndefined(countdown["cta_href"]) || "/products",
        deadline: stringOrUndefined(countdown["deadline"]) || "2026-12-31T23:59:59",
        backgroundColor: stringOrUndefined(countdown["background_color"]) || "#D0E9F3",
        backgroundImageUrl: storefrontImageUrl(stringOrUndefined(countdown["background_image_url"])) || "/images/countdown/countdown-bg.png",
        productImageUrl: storefrontImageUrl(stringOrUndefined(countdown["product_image_url"])) || "/images/countdown/countdown-01.png",
      },
      newsletter: {
        enabled: booleanOrDefault(newsletter["enabled"], false),
        title: stringOrUndefined(newsletter["title"]) || "Recibe novedades y ofertas",
        description:
          stringOrUndefined(newsletter["description"]) ||
          "Regístrate para recibir lanzamientos, descuentos y contenido de la tienda.",
        placeholder: stringOrUndefined(newsletter["placeholder"]) || "Tu correo electrónico",
        buttonLabel: stringOrUndefined(newsletter["button_label"]) || "Registrarme",
        backgroundImageUrl:
          storefrontImageUrl(stringOrUndefined(newsletter["background_image_url"])) || "/images/shapes/newsletter-bg.jpg",
      },
      testimonialsSection: {
        enabled: booleanOrDefault(testimonials["enabled"], false),
        eyebrow: stringOrUndefined(testimonials["eyebrow"]) || "Testimonios",
        title: stringOrUndefined(testimonials["title"]) || "Lo que dicen nuestros clientes",
      },
      testimonials: testimonialItems,
  };
}
