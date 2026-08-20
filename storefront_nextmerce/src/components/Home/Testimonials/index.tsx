"use client";

import { useCallback, useRef } from "react";
import type { Swiper as SwiperInstance } from "swiper";
import { Swiper, SwiperSlide } from "swiper/react";

import type { HomeTestimonials } from "@/types/home";
import type { Testimonial } from "@/types/testimonial";
import "swiper/css";
import SingleItem from "./SingleItem";

const Testimonials = ({ section, items }: { section: HomeTestimonials; items: Testimonial[] }) => {
  const sliderRef = useRef<{ swiper: SwiperInstance } | null>(null);
  const handlePrev = useCallback(() => sliderRef.current?.swiper.slidePrev(), []);
  const handleNext = useCallback(() => sliderRef.current?.swiper.slideNext(), []);

  if (!section.enabled || !items.length) return null;

  return (
    <section className="overflow-hidden bg-[#17233f] py-16 text-white sm:py-20 lg:py-24">
      <div className="mx-auto w-full max-w-[1240px] px-4 sm:px-8 xl:px-0">
        <div className="mb-9 flex items-end justify-between gap-5">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#d9a489]">{section.eyebrow}</p>
            <h2 className="max-w-[640px] text-[30px] font-semibold leading-tight tracking-[-0.025em] sm:text-[42px]">{section.title}</h2>
          </div>
          <div className="flex gap-2">
            <button type="button" aria-label="Anterior" onClick={handlePrev} className="flex h-10 w-10 items-center justify-center rounded-full border border-white/25 transition hover:bg-white hover:text-[#17233f]">
              <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true" className="rotate-180">
                <path d="M3 8.5h10M9.5 5l3.5 3.5L9.5 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <button type="button" aria-label="Siguiente" onClick={handleNext} className="flex h-10 w-10 items-center justify-center rounded-full border border-white/25 transition hover:bg-white hover:text-[#17233f]">
              <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true">
                <path d="M3 8.5h10M9.5 5l3.5 3.5L9.5 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>

        <Swiper
          ref={sliderRef}
          slidesPerView={1.08}
          spaceBetween={16}
          breakpoints={{ 640: { slidesPerView: 2, spaceBetween: 20 }, 1100: { slidesPerView: 3, spaceBetween: 22 } }}
        >
          {items.map((item, index) => (
            <SwiperSlide key={`${item.authorName}-${index}`}><SingleItem testimonial={item} /></SwiperSlide>
          ))}
        </Swiper>
      </div>
    </section>
  );
};

export default Testimonials;
