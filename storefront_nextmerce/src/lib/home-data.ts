import { Category } from "@/types/category";
import { HomeViewModel } from "@/types/home";
import { Product } from "@/types/product";
import { Testimonial } from "@/types/testimonial";
import { PublicCollection, PublicProduct } from "@/types/storefront";
import { getStorefrontBranding } from "./storefront-branding";
import { storefrontImageUrl } from "./storefront-image";
import { formatMoney } from "./money";

import {
  getPublicCollections,
  getPublicProducts,
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
  return formatMoney(value, currency, false);
}

function fallbackImage(_seed: string): string {
  return "/images/home/home-hero-editorial.webp";
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
    categoryName: product.category_name || undefined,
    brandName: product.brand_name || undefined,
    productType: product.product_type || undefined,
    availableSizes: product.available_sizes || [],
    availableColors: product.available_colors || [],
    variants: (product.variants || []).map((variant) => ({
      id: variant.id,
      name: variant.name,
      sku: variant.sku,
      attributes: variant.attributes || {},
      price: Number(variant.price),
      compareAtPrice: variant.compare_at_price == null ? undefined : Number(variant.compare_at_price),
      inStock: variant.in_stock,
      stockQuantity: variant.stock_quantity ?? undefined,
    })),
    reviews: 0,
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
    href: `/collections/${encodeURIComponent(collection.slug)}`,
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
  return [
    {
      review: "Aquí podrás mostrar una opinión real sobre la calidad, la entrega o la experiencia de compra.",
      authorName: "Cliente de ejemplo",
      authorRole: "Contenido demostrativo · editable en el panel",
      authorImg: "/images/users/user-01.jpg",
    },
    {
      review: "Usa este espacio para destacar lo que tus clientes más valoran de tus productos y tu servicio.",
      authorName: "Cliente de ejemplo",
      authorRole: "Contenido demostrativo · editable en el panel",
      authorImg: "/images/users/user-02.jpg",
    },
    {
      review: "Cuando agregues testimonios desde la configuración, estas tarjetas de muestra se reemplazarán.",
      authorName: "Cliente de ejemplo",
      authorRole: "Contenido demostrativo · editable en el panel",
      authorImg: "/images/users/user-03.jpg",
    },
  ];
}

function isLegacyTemplateTestimonial(item: Record<string, unknown>): boolean {
  const review = String(item["review"] || "").toLowerCase();
  const role = String(item["author_role"] || "").toLowerCase();
  return (
    review.includes("lorem ipsum") ||
    role === "serial entrepreneur" ||
    role === "backend developer"
  );
}

export async function loadHomeViewModel(): Promise<HomeViewModel> {
  const storefront = await resolveStorefront();
  const branding = getStorefrontBranding(storefront);
  const home = homeSettings(storefront);
  const [collections, catalog] = await Promise.all([
    getPublicCollections(storefront.id),
    getPublicProducts(storefront.id, { page: 1, page_size: 24, sort: "latest" }),
  ]);
  const categoryFallbackItems = collections.map(toTemplateCategory);
  const uniqueProducts = Array.from(new Map(catalog.items.map((product) => [product.id, product])).values());
  const featuredProducts = uniqueProducts.filter((product) => product.is_featured);
  const sortedProducts = (featuredProducts.length ? featuredProducts : uniqueProducts).slice();
  const productCategoryFallbackItems = Array.from(
    new Map(
      uniqueProducts
        .filter((product) => product.category_name)
        .map((product) => [product.category_name, product]),
    ).values(),
  ).slice(0, 6).map((product) => ({
    id: numericId(`category-${product.category_name}`),
    title: product.category_name || "Descubre más",
    img:
      storefrontImageUrl(product.image_url) ||
      storefrontImageUrl(product.gallery[0]) ||
      "/images/home/home-hero-editorial.webp",
    href: product.category_name
      ? `/products?category=${encodeURIComponent(product.category_name)}`
      : "/products",
    backgroundColor: "#EEEAE4",
    overlayOpacity: 0.08,
    imagePosition: "center",
  }));
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
  // Home v2 makes the previously hidden blocks visible once. After the
  // merchant saves the new configuration version, each switch is respected.
  const respectsVisibilitySettings = Number(home["content_version"] || 0) >= 2;

  const productHeroSlides = sortedProducts.slice(0, 1).map((product) => {
    return {
      id: product.id,
      title: product.title,
      description: product.description || `Conoce ${product.title} en la tienda online de ${storefront.name}.`,
      ctaHref: `/products/${encodeURIComponent(product.slug)}`,
      image: storefrontImageUrl(product.image_url) || storefrontImageUrl(product.gallery[0]) || fallbackImage(product.slug),
      overlayOpacity: 0.3,
      imagePosition: "center",
      contentAlignment: "left" as const,
      textColor: "#FFFFFF",
      buttonLabel: "Ver producto",
      buttonColor: "#B65332",
    };
  });

  const fallbackHeroSlides = [
    {
      id: "home-editorial",
      title: "Haz de tu casa tu lugar favorito",
      description: "Textiles, colores y detalles que transforman lo cotidiano en un espacio que se siente realmente tuyo.",
      ctaHref: "/products",
      image: "/images/home/home-hero-editorial.webp",
      overlayOpacity: 0.12,
      imagePosition: "center",
      contentAlignment: "left" as const,
      textColor: "#17233F",
      buttonLabel: "Descubrir la colección",
      buttonColor: "#17233F",
    },
    ...productHeroSlides,
  ];

  const fallbackHeroPromos = collections.slice(0, 2).map((collection, index) => {
    const sourceProduct = sortedProducts[index];
    const compare = sourceProduct?.compare_at_price ?? sourceProduct?.base_price ?? null;
    return {
      id: collection.id,
      title: collection.name,
      offerLabel: "Colección destacada",
      href: `/collections/${encodeURIComponent(collection.slug)}`,
      priceLabel: sourceProduct ? moneyLabel(storefront.currency, sourceProduct.price) : "Nuevo",
      comparePriceLabel: compare && sourceProduct && compare > sourceProduct.price ? moneyLabel(storefront.currency, compare) : undefined,
      image:
        storefrontImageUrl(collection.image_url) ||
        storefrontImageUrl(sourceProduct?.image_url) ||
        storefrontImageUrl(sourceProduct?.gallery?.[0]) ||
        fallbackImage(collection.slug),
      backgroundColor: index === 0 ? "#DDE6DE" : "#E9DDD2",
      backgroundImageUrl: undefined,
    };
  });

  sortedProducts.slice(fallbackHeroPromos.length, 2).forEach((product) => {
    const index = fallbackHeroPromos.length;
    fallbackHeroPromos.push({
      id: `product-promo-${product.id}`,
      title: product.category_name || product.title,
      offerLabel: "Selección para tu hogar",
      href: `/products/${encodeURIComponent(product.slug)}`,
      priceLabel: moneyLabel(storefront.currency, product.price),
      comparePriceLabel: undefined,
      image:
        storefrontImageUrl(product.image_url) ||
        storefrontImageUrl(product.gallery[0]) ||
        "/images/home/home-hero-editorial.webp",
      backgroundColor: index === 0 ? "#DDE6DE" : "#E9DDD2",
      backgroundImageUrl: undefined,
    });
  });

  while (fallbackHeroPromos.length < 2) {
    const index = fallbackHeroPromos.length;
    fallbackHeroPromos.push({
      id: `home-promo-${index + 1}`,
      title: index === 0 ? "Esenciales para descansar mejor" : "Detalles que renuevan tu espacio",
      offerLabel: "Inspiración para tu hogar",
      href: "/products",
      priceLabel: "Descubrir",
      comparePriceLabel: undefined,
      image: "/images/home/home-hero-editorial.webp",
      backgroundColor: index === 0 ? "#DDE6DE" : "#E9DDD2",
      backgroundImageUrl: undefined,
    });
  }

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

  const configuredHeroPromoItems = configuredHeroPromos
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
        .filter((promo) => promo.title);
  const heroPromos = [...configuredHeroPromoItems, ...fallbackHeroPromos]
    .filter((promo, index, all) => all.findIndex((item) => item.id === promo.id) === index)
    .slice(0, 2);

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
  const configuredTestimonials = arrayOfObjects(testimonials["items"]).filter(
    (item) => !isLegacyTemplateTestimonial(item),
  );
  const testimonialItems = configuredTestimonials.length
    ? configuredTestimonials
        .map((item) => ({
          review: stringOrUndefined(item["review"]) || "",
          authorName: stringOrUndefined(item["author_name"]) || "",
          authorRole: stringOrUndefined(item["author_role"]) || "",
          authorImg: storefrontImageUrl(stringOrUndefined(item["author_image"])) || "/images/users/user-01.jpg",
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
        ctaHref: banner.cta_href?.trim() || "/products",
        image: storefrontImageUrl(banner.image_url),
        backgroundColor: banner.background_color?.trim() || undefined,
        accentColor: banner.accent_color?.trim() || undefined,
      }))
    : (collections.length ? collections.slice(0, 3).map((collection, index) => {
        const sourceProduct = sortedProducts[index];
        return {
          id: `collection-promo-${collection.id}`,
          title: collection.name,
          subtitle: index === 0 ? "Ideas para renovar tus espacios" : "Hecho para disfrutar en casa",
          description:
            collection.description ||
            (index === 0
              ? "Encuentra texturas, colores y esenciales para darle una nueva sensación a cada rincón."
              : "Una selección pensada para combinar comodidad, funcionalidad y estilo."),
          ctaLabel: "Explorar colección",
          ctaHref: `/collections/${encodeURIComponent(collection.slug)}`,
          image:
            storefrontImageUrl(collection.image_url) ||
            storefrontImageUrl(sourceProduct?.image_url) ||
            storefrontImageUrl(sourceProduct?.gallery?.[0]) ||
            "/images/home/home-hero-editorial.webp",
          backgroundColor: index === 0 ? "#17233F" : index === 1 ? "#DDE6DE" : "#E9DDD2",
          accentColor: index === 0 ? "#F5EDE3" : "#17233F",
        };
      }) : [{
        id: "home-inspiration",
        title: "Renueva tu casa con detalles que se sienten",
        subtitle: "Ideas para transformar tus espacios",
        description: "Descubre una selección de textiles y esenciales pensados para disfrutar más cada rincón.",
        ctaLabel: "Ver todos los productos",
        ctaHref: "/products",
        image: "/images/home/home-hero-editorial.webp",
        backgroundColor: "#17233F",
        accentColor: "#F5EDE3",
      }]);

  return {
      storefrontId: storefront.id,
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
        : categoryFallbackItems.length
          ? categoryFallbackItems
          : productCategoryFallbackItems,
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
        enabled: respectsVisibilitySettings
          ? booleanOrDefault(countdown["enabled"], true)
          : true,
        eyebrow: stringOrUndefined(countdown["eyebrow"]) || "Oferta especial",
        title: stringOrUndefined(countdown["title"]) || "No te pierdas esta oportunidad",
        description: stringOrUndefined(countdown["description"]) || "Descubre productos seleccionados para ti.",
        ctaLabel: stringOrUndefined(countdown["cta_label"]) || "Ver oferta",
        ctaHref: stringOrUndefined(countdown["cta_href"]) || "/products",
        deadline: stringOrUndefined(countdown["deadline"]) || "2026-12-31T23:59:59",
        backgroundColor: stringOrUndefined(countdown["background_color"]) || "#D0E9F3",
        backgroundImageUrl: storefrontImageUrl(stringOrUndefined(countdown["background_image_url"])) || "/images/countdown/countdown-bg.png",
        productImageUrl: storefrontImageUrl(stringOrUndefined(countdown["product_image_url"])) || "/images/home/home-hero-editorial.webp",
      },
      newsletter: {
        enabled: respectsVisibilitySettings
          ? booleanOrDefault(newsletter["enabled"], true)
          : true,
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
        enabled: respectsVisibilitySettings
          ? booleanOrDefault(testimonials["enabled"], true)
          : true,
        eyebrow: configuredTestimonials.length
          ? stringOrUndefined(testimonials["eyebrow"]) || "Testimonios"
          : "Contenido de demostración",
        title: configuredTestimonials.length
          ? stringOrUndefined(testimonials["title"]) || "Lo que dicen nuestros clientes"
          : "Así se verán las historias de tus clientes",
      },
      testimonials: testimonialItems,
  };
}
