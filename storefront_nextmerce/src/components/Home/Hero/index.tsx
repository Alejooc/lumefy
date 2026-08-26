import Image from "next/image";
import Link from "next/link";

import type { HomeFeature, HeroPromo, HeroSlide } from "@/types/home";
import HeroCarousel from "./HeroCarousel";
import HeroFeature from "./HeroFeature";

const Hero = ({ slides, promos, features }: { slides: HeroSlide[]; promos: HeroPromo[]; features: HomeFeature[] }) => {
  if (!slides.length) return null;

  return (
    <section className="overflow-hidden bg-gray-1 pb-8 pt-[154px] sm:pt-40 lg:pb-11 lg:pt-28 xl:pt-48">
      <div className="mx-auto w-full max-w-[1240px] px-4 sm:px-8 xl:px-0">
        <div className="mb-5 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-dark-3">
          <span className="h-px w-9 bg-blue" />
          Una casa con intención
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.9fr)_minmax(300px,0.85fr)] lg:gap-5">
          <div className="min-w-0 overflow-hidden rounded-[26px] bg-gray-2 shadow-[0_24px_70px_rgba(28,39,76,0.10)]">
            <HeroCarousel slides={slides} />
          </div>

          <div className="grid min-w-0 grid-cols-2 gap-4 lg:grid-cols-1 lg:grid-rows-2 lg:gap-5">
            {promos.slice(0, 2).map((promo, index) => (
              <Link
                key={promo.id}
                href={promo.href}
                className="group relative min-h-[220px] overflow-hidden rounded-[22px] bg-blue-light-5 sm:min-h-[280px] lg:min-h-0"
                style={{ backgroundColor: promo.backgroundColor || (index === 0 ? "#E1E8FF" : "#F3F4F6") }}
              >
                <Image
                  src={promo.backgroundImageUrl || promo.image}
                  alt={promo.title}
                  fill
                  sizes="(max-width: 1024px) 50vw, 360px"
                  className="object-cover transition duration-700 group-hover:scale-[1.04]"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#101827]/90 via-[#101827]/15 to-transparent" />
                <div className="absolute inset-x-0 bottom-0 p-4 text-white sm:p-6">
                  <p className="mb-1 hidden text-[10px] font-semibold uppercase tracking-[0.2em] text-white/75 sm:block">
                    {promo.offerLabel || "Colección destacada"}
                  </p>
                  <h2 className="text-base font-semibold leading-tight sm:text-xl">{promo.title}</h2>
                  <div className="mt-2 flex items-end justify-between gap-2">
                    <span className="text-sm font-semibold sm:text-lg">{promo.priceLabel}</span>
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-[#17233f] transition group-hover:translate-x-1 sm:h-9 sm:w-9">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                        <path d="M3 8h9M8.5 4.5 12 8l-3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        <HeroFeature items={features} />
      </div>
    </section>
  );
};

export default Hero;
