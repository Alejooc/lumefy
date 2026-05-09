import React from "react";
import Image from "next/image";
import { HomeFeature } from "@/types/home";

const HeroFeature = ({ items }: { items: HomeFeature[] }) => {
  if (!items.length) {
    return null;
  }

  return (
    <div className="max-w-[1060px] w-full mx-auto px-4 sm:px-8 xl:px-0">
      <div className="mt-10 grid grid-cols-1 gap-x-7.5 gap-y-6 sm:grid-cols-2 xl:grid-cols-4 xl:gap-x-12.5">
        {items.map((item) => (
          <div className="flex min-w-0 items-start gap-4" key={item.id}>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center">
              <Image src={item.image} alt={item.title} width={40} height={41} />
            </div>

            <div className="min-w-0">
              <h3 className="font-medium text-lg leading-7 text-dark break-words">{item.title}</h3>
              <p className="text-sm leading-6 text-dark-4 break-words">{item.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HeroFeature;
