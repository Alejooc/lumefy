import { Category } from "@/types/category";
import { Product } from "@/types/product";
import { Testimonial } from "@/types/testimonial";

export type HeroSlide = {
  id: string;
  enabled?: boolean;
  title: string;
  description: string;
  ctaHref: string;
  image: string;
  overlayOpacity?: number;
  imagePosition?: string;
  contentAlignment?: "left" | "center";
  textColor?: string;
  buttonLabel?: string;
  buttonColor?: string;
};

export type HeroPromo = {
  id: string;
  enabled?: boolean;
  title: string;
  offerLabel?: string;
  href: string;
  priceLabel: string;
  comparePriceLabel?: string;
  image: string;
  backgroundColor?: string;
  backgroundImageUrl?: string;
};

export type HomeSection = {
  eyebrow?: string;
  title: string;
  ctaLabel?: string;
  ctaHref?: string;
};

export type HomeLayoutSectionType =
  | "hero"
  | "categories"
  | "new_arrivals"
  | "promo_banners"
  | "best_sellers"
  | "countdown"
  | "testimonials"
  | "newsletter"
  | "closing_cta"
  | "custom_embed";

export type HomeLayoutSection = {
  id: string;
  type: HomeLayoutSectionType;
  enabled: boolean;
  settings: Record<string, unknown>;
};

export type HomeCountdown = {
  enabled: boolean;
  eyebrow?: string;
  title: string;
  description?: string;
  ctaLabel?: string;
  ctaHref?: string;
  deadline?: string;
  backgroundColor?: string;
  backgroundImageUrl?: string;
  productImageUrl?: string;
};

export type HomeNewsletter = {
  enabled: boolean;
  title: string;
  description?: string;
  placeholder?: string;
  buttonLabel?: string;
  backgroundImageUrl?: string;
};

export type HomeFeature = {
  id: string;
  enabled?: boolean;
  title: string;
  description?: string;
  image: string;
};

export type HomeTestimonials = {
  enabled: boolean;
  eyebrow?: string;
  title: string;
};

export type HomeViewModel = {
  storefrontId: string;
  storeName: string;
  currency: string;
  sections: HomeLayoutSection[];
  heroSlides: HeroSlide[];
  heroPromos: HeroPromo[];
  features: HomeFeature[];
  promoBanners: HomePromoBanner[];
  categorySection: HomeSection;
  categories: Category[];
  newArrivalsSection: HomeSection;
  newArrivals: Product[];
  bestSellersSection: HomeSection;
  bestSellers: Product[];
  countdown: HomeCountdown;
  testimonialsSection: HomeTestimonials;
  testimonials: Testimonial[];
  newsletter: HomeNewsletter;
};

export type HomePromoBanner = {
  id: string;
  enabled?: boolean;
  title: string;
  subtitle?: string;
  description?: string;
  ctaLabel: string;
  ctaHref: string;
  image?: string;
  backgroundColor?: string;
  accentColor?: string;
};
