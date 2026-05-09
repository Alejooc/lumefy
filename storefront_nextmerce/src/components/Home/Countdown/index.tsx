"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";

import { HomeCountdown } from "@/types/home";

const CounDown = ({ content }: { content: HomeCountdown }) => {
  const [days, setDays] = useState(0);
  const [hours, setHours] = useState(0);
  const [minutes, setMinutes] = useState(0);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!content.enabled) {
      return;
    }

    const getTime = () => {
      const time = Date.parse(content.deadline || "") - Date.now();
      const safeTime = Number.isFinite(time) ? Math.max(time, 0) : 0;

      setDays(Math.floor(safeTime / (1000 * 60 * 60 * 24)));
      setHours(Math.floor((safeTime / (1000 * 60 * 60)) % 24));
      setMinutes(Math.floor((safeTime / 1000 / 60) % 60));
      setSeconds(Math.floor((safeTime / 1000) % 60));
    };

    getTime();
    const interval = setInterval(getTime, 1000);
    return () => clearInterval(interval);
  }, [content.deadline, content.enabled]);

  if (!content.enabled) {
    return null;
  }

  return (
    <section className="overflow-hidden py-20">
      <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
        <div
          className="relative overflow-hidden z-1 rounded-lg p-4 sm:p-7.5 lg:p-10 xl:p-15"
          style={{ backgroundColor: content.backgroundColor || "#D0E9F3" }}
        >
          <div className="max-w-[422px] w-full">
            {content.eyebrow ? (
              <span className="block font-medium text-custom-1 text-blue mb-2.5">
                {content.eyebrow}
              </span>
            ) : null}

            <h2 className="font-bold text-dark text-xl lg:text-heading-4 xl:text-heading-3 mb-3">
              {content.title}
            </h2>

            {content.description ? <p>{content.description}</p> : null}

            <div className="flex flex-wrap gap-6 mt-6">
              {[
                { label: "Days", value: days },
                { label: "Hours", value: hours },
                { label: "Minutes", value: minutes },
                { label: "Seconds", value: seconds },
              ].map((item) => (
                <div key={item.label}>
                  <span className="min-w-[64px] h-14.5 font-semibold text-xl lg:text-3xl text-dark rounded-lg flex items-center justify-center bg-white shadow-2 px-4 mb-2">
                    {item.value < 10 ? `0${item.value}` : item.value}
                  </span>
                  <span className="block text-custom-sm text-dark text-center">{item.label}</span>
                </div>
              ))}
            </div>

            <Link
              href={content.ctaHref || "/products"}
              className="inline-flex font-medium text-custom-sm text-white bg-blue py-3 px-9.5 rounded-md ease-out duration-200 hover:bg-blue-dark mt-7.5"
            >
              {content.ctaLabel || "Check it Out!"}
            </Link>
          </div>

          <Image
            src={content.backgroundImageUrl || "/images/countdown/countdown-bg.png"}
            alt="bg shapes"
            className="hidden sm:block absolute right-0 bottom-0 -z-1"
            width={737}
            height={482}
          />
          <Image
            src={content.productImageUrl || "/images/countdown/countdown-01.png"}
            alt="product"
            className="hidden lg:block absolute right-4 xl:right-33 bottom-4 xl:bottom-10 -z-1"
            width={411}
            height={376}
          />
        </div>
      </div>
    </section>
  );
};

export default CounDown;
