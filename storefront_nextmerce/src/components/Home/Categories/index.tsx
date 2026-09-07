"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { Category } from "@/types/category";
import type { HomeSection } from "@/types/home";
import SingleItem from "./SingleItem";

const Categories = ({ items, section }: { items: Category[]; section: HomeSection }) => {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [isBeginning, setIsBeginning] = useState(true);
  const [isEnd, setIsEnd] = useState(false);

  const syncNavigationState = useCallback(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    setIsBeginning(scroller.scrollLeft <= 1);
    setIsEnd(scroller.scrollLeft + scroller.clientWidth >= scroller.scrollWidth - 1);
  }, []);

  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;

    let frame = 0;
    const handleScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(syncNavigationState);
    };
    const observer = new ResizeObserver(syncNavigationState);
    observer.observe(scroller);
    scroller.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      scroller.removeEventListener("scroll", handleScroll);
    };
  }, [items.length, syncNavigationState]);

  const move = (direction: -1 | 1) => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    scroller.scrollBy({ left: direction * scroller.clientWidth * 0.82, behavior: "smooth" });
  };

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
            <button
              type="button"
              aria-label="Categoría anterior"
              disabled={isBeginning}
              onClick={() => move(-1)}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-[#dcd5cc] text-[#17233f] transition hover:border-[#17233f] hover:bg-[#17233f] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true" className="rotate-180">
                <path d="M3 8.5h10M9.5 5l3.5 3.5L9.5 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <button
              type="button"
              aria-label="Categoría siguiente"
              disabled={isEnd}
              onClick={() => move(1)}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-[#dcd5cc] text-[#17233f] transition hover:border-[#17233f] hover:bg-[#17233f] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true">
                <path d="M3 8.5h10M9.5 5l3.5 3.5L9.5 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>

        <div
          ref={scrollerRef}
          className="grid snap-x snap-mandatory grid-flow-col auto-cols-[calc((100%-14px)/2.05)] gap-3.5 overflow-x-auto scroll-smooth [scrollbar-width:none] sm:auto-cols-[calc((100%-36px)/3.15)] sm:gap-[18px] lg:auto-cols-[calc((100%-60px)/4.25)] lg:gap-5 xl:auto-cols-[calc((100%-88px)/5)] xl:gap-[22px] [&::-webkit-scrollbar]:hidden"
        >
          {items.map((item) => (
            <div key={item.id} className="min-w-0 snap-start">
              <SingleItem item={item} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Categories;
