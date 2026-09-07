"use client";

import { Autoplay, Pagination } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/react";
import "swiper/css";
import "swiper/css/pagination";

import type { HeroSlide } from "@/types/home";
import HeroSlideContent from "./HeroSlideContent";

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
      {slides.map((slide, index) => (
        <SwiperSlide key={slide.id}>
          <HeroSlideContent slide={slide} headingLevel={index === 0 ? 1 : 2} />
        </SwiperSlide>
      ))}
    </Swiper>
  );
};

export default HeroCarousel;
