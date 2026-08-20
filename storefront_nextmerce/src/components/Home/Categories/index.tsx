"use client";

import { useCallback, useEffect, useState } from "react";
import type { Swiper as SwiperInstance } from "swiper";
import { Swiper, SwiperSlide } from "swiper/react";

import type { Category } from "@/types/category";
import type { HomeSection } from "@/types/home";
import "swiper/css";
import SingleItem from "./SingleItem";

const Categories = ({ items, section }: { items: Category[]; section: HomeSection }) => {
  const [swiper, setSwiper] = useState<SwiperInstance | null>(null);
  const [isBeginning, setIsBeginning] = useState(true);
  const [isEnd, setIsEnd] = useState(false);

  const syncNavigationState = useCallback((instance: SwiperInstance | null) => {
    if (!instance) return;
    instance.update();
    setIsBeginning(instance.isBeginning);
    setIsEnd(instance.isEnd);
  }, []);

  useEffect(() => syncNavigationState(swiper), [swiper, items.length, syncNavigationState]);
  if (!items.length) return null;

  return (
    <section className="overflow-hidden bg-white py-16 sm:py-20 lg:py-24">
      <div className="mx-auto w-full max-w-[1240px] px-4 sm:px-8 xl:px-0">
        <div className="mb-8 flex items-end justify-between gap-5 sm:mb-10">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#b65332]">{section.eyebrow || "Explora"}</p>
            <h2 className="max-w-[620px] text-[30px] font-semibold leading-tight tracking-[-0.025em] text-[#17233f] sm:text-[42px]">
              {section.title}
            </h2>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {[
              { label: "Categoría anterior", disabled: isBeginning, action: () => swiper?.slidePrev(), direction: "left" },
              { label: "Categoría siguiente", disabled: isEnd, action: () => swiper?.slideNext(), direction: "right" },
            ].map((button) => (
              <button
                key={button.label}
                type="button"
                aria-label={button.label}
                disabled={!swiper || button.disabled}
                onClick={button.action}
                className="flex h-10 w-10 items-center justify-center rounded-full border border-[#dcd5cc] text-[#17233f] transition hover:border-[#17233f] hover:bg-[#17233f] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true" className={button.direction === "left" ? "rotate-180" : ""}>
                  <path d="M3 8.5h10M9.5 5l3.5 3.5L9.5 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            ))}
          </div>
        </div>

        <Swiper
          onSwiper={(instance) => { setSwiper(instance); syncNavigationState(instance); }}
          onSlideChange={syncNavigationState}
          onResize={syncNavigationState}
          observer
          observeParents
          watchOverflow
          spaceBetween={14}
          breakpoints={{
            0: { slidesPerView: 2.05 },
            640: { slidesPerView: 3.15, spaceBetween: 18 },
            1024: { slidesPerView: 4.25, spaceBetween: 20 },
            1280: { slidesPerView: 5, spaceBetween: 22 },
          }}
        >
          {items.map((item) => (
            <SwiperSlide key={item.id}>
              <SingleItem item={item} />
            </SwiperSlide>
          ))}
        </Swiper>
      </div>
    </section>
  );
};

export default Categories;
