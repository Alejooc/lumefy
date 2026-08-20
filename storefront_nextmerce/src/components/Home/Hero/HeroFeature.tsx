import Image from "next/image";

import type { HomeFeature } from "@/types/home";

const HeroFeature = ({ items }: { items: HomeFeature[] }) => {
  if (!items.length) return null;

  return (
    <div className="relative z-20 -mt-1 grid overflow-hidden rounded-[20px] border border-[#dfd7cc] bg-white/95 shadow-[0_18px_45px_rgba(49,43,34,0.08)] sm:grid-cols-2 lg:-mt-7 lg:grid-cols-4">
      {items.slice(0, 4).map((item, index) => (
        <div
          className={`flex min-w-0 items-center gap-3.5 px-4 py-4 sm:px-5 lg:py-5 ${index ? "border-t border-[#ebe5dd] sm:border-t-0 sm:border-l" : ""} ${index === 2 ? "sm:border-l-0 lg:border-l" : ""}`}
          key={item.id}
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#f4f0e9]">
            <Image src={item.image} alt="" width={24} height={24} />
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold leading-5 text-[#17233f]">{item.title}</h3>
            <p className="mt-0.5 text-xs leading-5 text-[#6c7180]">{item.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

export default HeroFeature;
