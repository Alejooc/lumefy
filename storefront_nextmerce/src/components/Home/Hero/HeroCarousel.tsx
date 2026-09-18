"use client";

import { useState } from "react";

import type { HeroSlide } from "@/types/home";
import HeroSlideContent from "./HeroSlideContent";

const HeroCarousel = ({ slides }: { slides: HeroSlide[] }) => {
  const [activeIndex, setActiveIndex] = useState(0);

  if (!slides.length) return null;

  return (
    <div
      className="relative h-full"
      aria-roledescription="carrusel"
      aria-label="Promociones destacadas"
    >
      {slides.map((slide, index) => (
        <div key={slide.id} hidden={index !== activeIndex} aria-hidden={index !== activeIndex}>
          <HeroSlideContent slide={slide} headingLevel={index === 0 ? 1 : 2} />
        </div>
      ))}

      <div className="absolute bottom-5 left-0 z-20 flex w-full items-center justify-center gap-2" aria-label="Seleccionar promoción">
        {slides.map((slide, index) => (
          <button
            key={slide.id}
            type="button"
            aria-label={`Ver promoción ${index + 1}`}
            aria-current={index === activeIndex ? "true" : undefined}
            onClick={() => setActiveIndex(index)}
            className="flex h-8 w-8 items-center justify-center rounded-full"
          >
            <span
              aria-hidden="true"
              className={`h-1.5 rounded-full bg-[#17233f] transition-[width,opacity] duration-200 ${
                index === activeIndex ? "w-6 opacity-100" : "w-1.5 opacity-[0.35]"
              }`}
            />
          </button>
        ))}
      </div>
    </div>
  );
};

export default HeroCarousel;
