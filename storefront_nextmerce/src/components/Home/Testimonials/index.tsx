"use client";

import { useRef } from "react";

import type { HomeTestimonials } from "@/types/home";
import type { Testimonial } from "@/types/testimonial";
import SingleItem from "./SingleItem";

const Testimonials = ({ section, items }: { section: HomeTestimonials; items: Testimonial[] }) => {
  const scrollerRef = useRef<HTMLDivElement>(null);

  const move = (direction: -1 | 1) => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    scroller.scrollBy({ left: direction * scroller.clientWidth * 0.9, behavior: "smooth" });
  };

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
            <button type="button" aria-label="Anterior" onClick={() => move(-1)} className="flex h-10 w-10 items-center justify-center rounded-full border border-white/25 transition hover:bg-white hover:text-[#17233f]">
              <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true" className="rotate-180">
                <path d="M3 8.5h10M9.5 5l3.5 3.5L9.5 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <button type="button" aria-label="Siguiente" onClick={() => move(1)} className="flex h-10 w-10 items-center justify-center rounded-full border border-white/25 transition hover:bg-white hover:text-[#17233f]">
              <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true">
                <path d="M3 8.5h10M9.5 5l3.5 3.5L9.5 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>

        <div
          ref={scrollerRef}
          className="grid snap-x snap-mandatory grid-flow-col auto-cols-[92%] gap-4 overflow-x-auto scroll-smooth [scrollbar-width:none] sm:auto-cols-[calc((100%-20px)/2)] sm:gap-5 min-[1100px]:auto-cols-[calc((100%-44px)/3)] min-[1100px]:gap-[22px] [&::-webkit-scrollbar]:hidden"
        >
          {items.map((item, index) => (
            <div key={`${item.authorName}-${index}`} className="min-w-0 snap-start"><SingleItem testimonial={item} /></div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Testimonials;
