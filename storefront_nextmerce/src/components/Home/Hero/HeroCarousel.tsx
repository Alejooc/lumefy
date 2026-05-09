"use client";
import { Swiper, SwiperSlide } from "swiper/react";
import { Autoplay, Pagination } from "swiper/modules";
import Link from "next/link";

import { HeroSlide } from "@/types/home";

import "swiper/css/pagination";
import "swiper/css";

const HeroCarousal = ({ slides }: { slides: HeroSlide[] }) => {
  if (!slides.length) {
    return null;
  }

  return (
    <Swiper
      spaceBetween={30}
      centeredSlides={true}
      autoplay={{
        delay: 2500,
        disableOnInteraction: false,
      }}
      pagination={{
        clickable: true,
      }}
      modules={[Autoplay, Pagination]}
      className="hero-carousel"
    >
      {slides.map((slide) => (
        <SwiperSlide key={slide.id}>
          {(() => {
            const textColor = slide.textColor || "#1C274C";
            const buttonColor = slide.buttonColor || "#1C274C";

            return (
          <div
            className="relative overflow-hidden"
            style={{
              backgroundImage: `url(${slide.image})`,
              backgroundSize: "cover",
              backgroundPosition: slide.imagePosition || "center",
            }}
          >
            <div
              className="absolute inset-0"
              style={{ backgroundColor: `rgba(255,255,255,${typeof slide.overlayOpacity === "number" ? Math.min(Math.max(slide.overlayOpacity, 0), 1) : 0.72})` }}
            />
            <div
              className={`relative z-10 py-10 px-4 sm:px-7.5 sm:py-15 lg:px-12.5 lg:py-24.5 ${slide.contentAlignment === "center" ? "mx-auto max-w-[620px] text-center" : "max-w-[394px]"}`}
              style={{ color: textColor }}
            >
              <h1 className="mb-3 text-xl font-semibold sm:text-3xl" style={{ color: textColor }}>
                <Link href={slide.ctaHref}>{slide.title}</Link>
              </h1>

              <p>{slide.description}</p>

              <Link
                href={slide.ctaHref}
                className="inline-flex font-medium text-white text-custom-sm rounded-md bg-dark py-3 px-9 ease-out duration-200 hover:bg-blue mt-10"
                style={{ backgroundColor: buttonColor }}
              >
                {slide.buttonLabel || "Shop Now"}
              </Link>
            </div>
          </div>
            );
          })()}
        </SwiperSlide>
      ))}
    </Swiper>
  );
};

export default HeroCarousal;
