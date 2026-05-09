import React from "react";
import Image from "next/image";
import Link from "next/link";

import { HomePromoBanner } from "@/types/home";

const fallbackPromos = ["/images/promo/promo-01.png", "/images/promo/promo-02.png", "/images/promo/promo-03.png"];

const PromoBanner = ({ items }: { items: HomePromoBanner[] }) => {
  const [primary, ...secondary] = items.slice(0, 3);

  if (!primary) {
    return null;
  }

  return (
    <section className="overflow-hidden py-20">
      <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
        <div
          className="relative z-1 overflow-hidden rounded-lg py-12.5 lg:py-17.5 xl:py-22.5 px-4 sm:px-7.5 lg:px-14 xl:px-19 mb-7.5"
          style={{ backgroundColor: primary.backgroundColor || "#F5F5F7" }}
        >
          <div className="max-w-[550px] w-full">
            {primary.subtitle ? (
              <span className="block font-medium text-xl text-dark mb-3">
                {primary.subtitle}
              </span>
            ) : null}

            <h2 className="font-bold text-xl lg:text-heading-4 xl:text-heading-3 text-dark mb-5">
              {primary.title}
            </h2>

            {primary.description ? <p>{primary.description}</p> : null}

            <Link
              href={primary.ctaHref}
              className="inline-flex font-medium text-custom-sm text-white bg-blue py-[11px] px-9.5 rounded-md ease-out duration-200 hover:bg-blue-dark mt-7.5"
            >
              {primary.ctaLabel}
            </Link>
          </div>

          <Image
            src={primary.image || fallbackPromos[0]}
            alt={primary.title}
            className="absolute bottom-0 right-4 lg:right-26 -z-1"
            width={274}
            height={350}
          />
        </div>

        <div className="grid gap-7.5 grid-cols-1 lg:grid-cols-2">
          {secondary.map((promo, index) => {
            const isLeft = index === 0;
            const buttonClass = isLeft ? "bg-teal hover:bg-teal-dark" : "bg-orange hover:bg-orange-dark";
            const imageClass = isLeft
              ? "absolute top-1/2 -translate-y-1/2 left-3 sm:left-10 -z-1"
              : "absolute top-1/2 -translate-y-1/2 right-3 sm:right-8.5 -z-1";
            const wrapperClass = isLeft ? "text-right" : "";

            return (
              <div
                key={promo.id}
                className="relative z-1 overflow-hidden rounded-lg py-10 xl:py-16 px-4 sm:px-7.5 xl:px-10"
                style={{ backgroundColor: promo.backgroundColor || (isLeft ? "#DBF4F3" : "#FFECE1") }}
              >
                <Image
                  src={promo.image || fallbackPromos[index + 1] || fallbackPromos[0]}
                  alt={promo.title}
                  className={imageClass}
                  width={isLeft ? 241 : 200}
                  height={isLeft ? 241 : 200}
                />

                <div className={wrapperClass}>
                  {promo.subtitle ? (
                    <span className="block text-lg text-dark mb-1.5">
                      {promo.subtitle}
                    </span>
                  ) : null}

                  <h2 className="font-bold text-xl lg:text-heading-4 text-dark mb-2.5">
                    {promo.title}
                  </h2>

                  {promo.description ? (
                    <p
                      className={isLeft ? "font-semibold text-custom-1" : "max-w-[285px] text-custom-sm"}
                      style={promo.accentColor ? { color: promo.accentColor } : undefined}
                    >
                      {promo.description}
                    </p>
                  ) : null}

                  <Link
                    href={promo.ctaHref}
                    className={`inline-flex font-medium text-custom-sm text-white py-2.5 px-8.5 rounded-md ease-out duration-200 mt-7.5 ${buttonClass}`}
                  >
                    {promo.ctaLabel}
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default PromoBanner;
