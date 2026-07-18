import { Category } from "@/types/category";
import { HomeViewModel } from "@/types/home";
import { Product } from "@/types/product";
import { Testimonial } from "@/types/testimonial";
import { PublicCollection, PublicProduct } from "@/types/storefront";
import { getStorefrontBranding } from "./storefront-branding";

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
  const previewImage = product.image_url || product.gallery[0] || fallbackImage(product.slug);
  const secondaryImage = product.gallery[1] || product.image_url || fallbackImage(`${product.slug}-alt`);
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
    img: collection.image_url || fallbackImage(collection.slug),
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
      title: "Free Shipping",
      description: "For all orders $200",
      image: "/images/icons/icon-01.svg",
    },
    {
      id: "feature-2",
      title: "1 & 1 Returns",
      description: "Cancellation after 1 day",
      image: "/images/icons/icon-02.svg",
    },
    {
      id: "feature-3",
      title: "100% Secure Payments",
      description: "Gurantee secure payments",
      image: "/images/icons/icon-03.svg",
    },
    {
      id: "feature-4",
      title: "24/7 Dedicated Support",
      description: "Anywhere & anytime",
      image: "/images/icons/icon-04.svg",
    },
  ];
}

function defaultTestimonials(): Testimonial[] {
  return [
    {
      review: "Lorem ipsum dolor sit amet, adipiscing elit. Donec malesuada justo vitaeaugue suscipit beautiful vehicula",
      authorName: "Davis Dorwart",
      authorImg: "/images/users/user-01.jpg",
      authorRole: "Serial Entrepreneur",
    },
    {
      review: "Lorem ipsum dolor sit amet, adipiscing elit. Donec malesuada justo vitaeaugue suscipit beautiful vehicula",
      authorName: "Wilson Dias",
      authorImg: "/images/users/user-02.jpg",
      authorRole: "Backend Developer",
    },
    {
      review: "Lorem ipsum dolor sit amet, adipiscing elit. Donec malesuada justo vitaeaugue suscipit beautiful vehicula",
      authorName: "Miracle Exterm",
      authorImg: "/images/users/user-03.jpg",
      authorRole: "Serial Entrepreneur",
    },
  ];
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
      description: product.description || `Explore ${product.title} in the online storefront of ${storefront.name}.`,
      ctaHref: `/products/${encodeURIComponent(product.slug)}`,
      image: product.image_url || product.gallery[0] || fallbackImage(product.slug),
      overlayOpacity: 0.72,
      imagePosition: "center",
      contentAlignment: "left" as const,
      textColor: "#1C274C",
      buttonLabel: "Shop Now",
      buttonColor: "#1C274C",
    };
  });

  const fallbackHeroPromos = detailedCollections.slice(0, 2).map((collection, index) => {
    const sourceProduct = collection.products?.[0] || sortedProducts[index];
    const compare = sourceProduct?.compare_at_price ?? sourceProduct?.base_price ?? null;
    return {
      id: collection.id,
      title: collection.name,
      offerLabel: "limited time offer",
      href: `/products?collection=${encodeURIComponent(collection.slug)}`,
      priceLabel: sourceProduct ? moneyLabel(storefront.currency, sourceProduct.price) : "New",
      comparePriceLabel: compare && sourceProduct && compare > sourceProduct.price ? moneyLabel(storefront.currency, compare) : undefined,
      image: collection.image_url || sourceProduct?.image_url || sourceProduct?.gallery?.[0] || fallbackImage(collection.slug),
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
          image: stringOrUndefined(slide["image"]) || fallbackImage(`hero-${index + 1}`),
          overlayOpacity: Number(slide["overlay_opacity"] ?? 0.72),
          imagePosition: stringOrUndefined(slide["image_position"]) || "center",
          contentAlignment: stringOrUndefined(slide["content_alignment"]) === "center" ? "center" as const : "left" as const,
          textColor: stringOrUndefined(slide["text_color"]) || "#1C274C",
          buttonLabel: stringOrUndefined(slide["button_label"]) || "Shop Now",
          buttonColor: stringOrUndefined(slide["button_color"]) || "#1C274C",
        }))
        .filter((slide) => slide.title)
    : fallbackHeroSlides;

  const heroPromos = configuredHeroPromos.length
    ? configuredHeroPromos
        .map((promo, index) => ({
          id: String(promo["id"] || `hero-promo-${index + 1}`),
          title: stringOrUndefined(promo["title"]) || "",
          offerLabel: stringOrUndefined(promo["offer_label"]) || "limited time offer",
          href: stringOrUndefined(promo["href"]) || "/products",
          priceLabel: stringOrUndefined(promo["price_label"]) || "New",
          comparePriceLabel: stringOrUndefined(promo["compare_price_label"]),
          image: stringOrUndefined(promo["image"]) || fallbackImage(`hero-promo-${index + 1}`),
          backgroundColor: stringOrUndefined(promo["background_color"]) || "#FFFFFF",
          backgroundImageUrl: stringOrUndefined(promo["background_image_url"]),
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
          image: stringOrUndefined(feature["image"]) || `/images/icons/icon-0${(index % 4) + 1}.svg`,
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
        ctaLabel: stringOrUndefined(banner["cta_label"]) || "Buy Now",
        ctaHref: stringOrUndefined(banner["cta_href"]) || "/products",
        image: stringOrUndefined(banner["image_url"]),
        backgroundColor: stringOrUndefined(banner["background_color"]),
        accentColor: stringOrUndefined(banner["accent_color"]),
      })).filter((banner) => banner.title)
    : branding.promoBanners.length
    ? branding.promoBanners.slice(0, 3).map((banner) => ({
        id: banner.id,
        title: banner.title,
        subtitle: banner.subtitle || undefined,
        description: banner.description || undefined,
        ctaLabel: banner.cta_label?.trim() || "Buy Now",
        ctaHref: banner.cta_href?.trim() || "#",
        image: banner.image_url?.trim() || undefined,
        backgroundColor: banner.background_color?.trim() || undefined,
        accentColor: banner.accent_color?.trim() || undefined,
      }))
    : [
        {
          id: "promo-1",
          title: "Apple iPhone 14 Plus",
          description:
            "iPhone 14 has the same superspeedy chip that's in iPhone 13 Pro, A15 Bionic, with a 5-core GPU, powers all the latest features.",
          ctaLabel: "Buy Now",
          ctaHref: "/products",
          image: "/images/promo/promo-01.png",
          backgroundColor: "#F5F5F7",
        },
        {
          id: "promo-2",
          title: "Workout At Home",
          subtitle: "Foldable Motorised Treadmill",
          description: "Flat 20% off",
          ctaLabel: "Grab Now",
          ctaHref: "/products",
          image: "/images/promo/promo-02.png",
          backgroundColor: "#DBF4F3",
          accentColor: "#10B981",
        },
        {
          id: "promo-3",
          title: "Up to 40% off",
          subtitle: "Apple Watch Ultra",
          description:
            "The aerospace-grade titanium case strikes the perfect balance of everything.",
          ctaLabel: "Buy Now",
          ctaHref: "/products",
          image: "/images/promo/promo-03.png",
          backgroundColor: "#FFECE1",
          accentColor: "#FB923C",
        },
      ];

  return {
      storeName: storefront.name,
      currency: storefront.currency,
      heroSlides,
      heroPromos,
      features,
      promoBanners,
      categorySection: {
        eyebrow: stringOrUndefined(categorySection["eyebrow"]) || "Categories",
        title: stringOrUndefined(categorySection["title"]) || "Browse by Category",
      },
      categories: configuredCategoryCards.length
        ? configuredCategoryCards
            .map((card, index) => ({
              id: numericId(String(card["id"] || `category-card-${index + 1}`)),
              title: stringOrUndefined(card["title"]) || "",
              img: stringOrUndefined(card["image"]) || fallbackImage(`category-card-${index + 1}`),
              href: stringOrUndefined(card["href"]) || "/products",
              backgroundColor: stringOrUndefined(card["background_color"]) || "#F2F3F8",
              overlayOpacity: Number(card["overlay_opacity"] ?? 0.18),
              imagePosition: stringOrUndefined(card["image_position"]) || "center",
            }))
            .filter((card) => card.title)
        : categoryFallbackItems,
      newArrivalsSection: {
        eyebrow: stringOrUndefined(newArrivalsSection["eyebrow"]) || "This Week's",
        title: stringOrUndefined(newArrivalsSection["title"]) || "New Arrivals",
        ctaLabel: stringOrUndefined(newArrivalsSection["cta_label"]) || "View All",
        ctaHref: stringOrUndefined(newArrivalsSection["cta_href"]) || "/products",
      },
      newArrivals: uniqueProducts.slice(0, 8).map(toTemplateProduct),
      bestSellersSection: {
        eyebrow: stringOrUndefined(bestSellersSection["eyebrow"]) || "This Month",
        title: stringOrUndefined(bestSellersSection["title"]) || "Best Sellers",
        ctaLabel: stringOrUndefined(bestSellersSection["cta_label"]) || "View All",
        ctaHref: stringOrUndefined(bestSellersSection["cta_href"]) || "/products",
      },
      bestSellers: (featuredProducts.length ? featuredProducts : uniqueProducts).slice(0, 6).map(toTemplateProduct),
      countdown: {
        enabled: booleanOrDefault(countdown["enabled"], true),
        eyebrow: stringOrUndefined(countdown["eyebrow"]) || "Don't Miss!!",
        title: stringOrUndefined(countdown["title"]) || "Enhance Your Music Experience",
        description: stringOrUndefined(countdown["description"]) || "The Havit H206d is a wired PC headphone.",
        ctaLabel: stringOrUndefined(countdown["cta_label"]) || "Check it Out!",
        ctaHref: stringOrUndefined(countdown["cta_href"]) || "/products",
        deadline: stringOrUndefined(countdown["deadline"]) || "2026-12-31T23:59:59",
        backgroundColor: stringOrUndefined(countdown["background_color"]) || "#D0E9F3",
        backgroundImageUrl: stringOrUndefined(countdown["background_image_url"]) || "/images/countdown/countdown-bg.png",
        productImageUrl: stringOrUndefined(countdown["product_image_url"]) || "/images/countdown/countdown-01.png",
      },
      newsletter: {
        enabled: booleanOrDefault(newsletter["enabled"], true),
        title: stringOrUndefined(newsletter["title"]) || "Don't Miss Out Latest Trends & Offers",
        description:
          stringOrUndefined(newsletter["description"]) ||
          "Register to receive news about the latest offers & discount codes",
        placeholder: stringOrUndefined(newsletter["placeholder"]) || "Enter your email",
        buttonLabel: stringOrUndefined(newsletter["button_label"]) || "Subscribe",
        backgroundImageUrl:
          stringOrUndefined(newsletter["background_image_url"]) || "/images/shapes/newsletter-bg.jpg",
      },
      testimonialsSection: {
        enabled: booleanOrDefault(testimonials["enabled"], true),
        eyebrow: stringOrUndefined(testimonials["eyebrow"]) || "Testimonials",
        title: stringOrUndefined(testimonials["title"]) || "User Feedbacks",
      },
      testimonials: testimonialItems,
  };
}
