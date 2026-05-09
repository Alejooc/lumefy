import React from "react";
import HeroCarousel from "./HeroCarousel";
import HeroFeature from "./HeroFeature";
import Image from "next/image";
import Link from "next/link";

import type { HomeFeature, HeroPromo, HeroSlide } from "@/types/home";

const Hero = ({ slides, promos, features }: { slides: HeroSlide[]; promos: HeroPromo[]; features: HomeFeature[] }) => {
  return (
    <section className="overflow-hidden pb-10 lg:pb-12.5 xl:pb-15 pt-57.5 sm:pt-45 lg:pt-30 xl:pt-51.5 bg-[#E5EAF4]">
      <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
        <div className="flex flex-wrap gap-5">
          <div className="xl:max-w-[757px] w-full">
            <div className="relative z-1 rounded-[10px] bg-white overflow-hidden">
              <Image
                src="/images/hero/hero-bg.png"
                alt="hero bg shapes"
                className="absolute right-0 bottom-0 -z-1"
                width={534}
                height={520}
              />

              <HeroCarousel slides={slides} />
            </div>
          </div>

          <div className="xl:max-w-[393px] w-full">
            <div className="flex flex-col sm:flex-row xl:flex-col gap-5">
              {promos.map((promo) => (
                <Link
                  key={promo.id}
                  href={promo.href}
                  className="w-full relative rounded-[10px] p-4 sm:p-7.5 overflow-hidden"
                  style={{
                    backgroundColor: promo.backgroundColor || "#FFFFFF",
                    backgroundImage: promo.backgroundImageUrl ? `url(${promo.backgroundImageUrl})` : undefined,
                    backgroundSize: promo.backgroundImageUrl ? "cover" : undefined,
                    backgroundPosition: promo.backgroundImageUrl ? "center" : undefined,
                  }}
                >
                  <div className="flex items-center gap-14">
                    <div>
                      <h2 className="max-w-[153px] font-semibold text-dark text-xl mb-20">{promo.title}</h2>

                      <div>
                        <p className="font-medium text-dark-4 text-custom-sm mb-1.5">{promo.offerLabel || "Oferta especial"}</p>
                        <span className="flex items-center gap-3">
                          <span className="font-medium text-heading-5 text-red">{promo.priceLabel}</span>
                          {promo.comparePriceLabel ? (
                            <span className="font-medium text-2xl text-dark-4 line-through">{promo.comparePriceLabel}</span>
                          ) : null}
                        </span>
                      </div>
                    </div>

                    <div>
                      <Image src={promo.image} alt={promo.title} width={123} height={161} />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>

      <HeroFeature items={features} />
    </section>
  );
};

export default Hero;
