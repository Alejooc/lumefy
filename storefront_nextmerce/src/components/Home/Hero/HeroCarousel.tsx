"use client";

import Image from "next/image";
import Link from "next/link";
import { Autoplay, Pagination } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/react";

import type { HeroSlide } from "@/types/home";
import "swiper/css";
import "swiper/css/pagination";

const HeroCarousel = ({ slides }: { slides: HeroSlide[] }) => {
  if (!slides.length) return null;

  return (
    <Swiper
      autoplay={{ delay: 5200, disableOnInteraction: false, pauseOnMouseEnter: true }}
      loop={slides.length > 1}
      pagination={{ clickable: true }}
      modules={[Autoplay, Pagination]}
      className="home-hero-carousel h-full"
    >
      {slides.map((slide, index) => {
        const textColor = slide.textColor || "#17233f";
        return (
          <SwiperSlide key={slide.id}>
            <article className="relative min-h-[500px] overflow-hidden sm:min-h-[590px] lg:min-h-[630px]">
              <Image
                src={slide.image}
                alt={slide.title}
                fill
                priority={index === 0}
                sizes="(max-width: 1024px) 100vw, 820px"
                className="object-cover"
                style={{ objectPosition: slide.imagePosition || "center" }}
              />
              <div
                className="absolute inset-0"
                style={{
                  background:
                    textColor.toLowerCase() === "#ffffff"
                      ? "linear-gradient(90deg, rgba(12,19,31,.78) 0%, rgba(12,19,31,.38) 48%, rgba(12,19,31,.05) 78%)"
                      : `linear-gradient(90deg, rgba(248,244,237,${Math.max(slide.overlayOpacity || 0.12, 0.72)}) 0%, rgba(248,244,237,.54) 43%, rgba(248,244,237,.02) 76%)`,
                }}
              />

              <div
                className={`relative z-10 flex min-h-[500px] flex-col justify-end px-6 pb-16 pt-20 sm:min-h-[590px] sm:px-10 sm:pb-20 lg:min-h-[630px] lg:px-14 ${
                  slide.contentAlignment === "center" ? "mx-auto max-w-[680px] items-center text-center" : "max-w-[570px] items-start"
                }`}
                style={{ color: textColor }}
              >
                <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.24em] opacity-75">Vive bonito todos los días</p>
                <h1 className="max-w-[540px] text-[38px] font-semibold leading-[1.03] tracking-[-0.035em] sm:text-[54px] lg:text-[62px]">
                  {slide.title}
                </h1>
                <p className="mt-5 max-w-[480px] text-sm leading-7 opacity-85 sm:text-base">{slide.description}</p>
                <Link
                  href={slide.ctaHref}
                  className="mt-7 inline-flex items-center gap-3 rounded-full px-6 py-3.5 text-sm font-semibold text-white shadow-[0_10px_28px_rgba(15,23,42,.18)] transition hover:-translate-y-0.5"
                  style={{ backgroundColor: slide.buttonColor || "#17233f" }}
                >
                  {slide.buttonLabel || "Ver productos"}
                  <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true">
                    <path d="M3 8.5h10M9.5 5l3.5 3.5L9.5 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </Link>
              </div>
            </article>
          </SwiperSlide>
        );
      })}
    </Swiper>
  );
};

export default HeroCarousel;
