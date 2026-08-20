import Link from "next/link";

import ProductItem from "@/components/Common/ProductItem";
import type { HomeSection } from "@/types/home";
import type { Product } from "@/types/product";

const BestSeller = ({ items, section }: { items: Product[]; section: HomeSection }) => {
  if (!items.length) return null;

  return (
    <section className="overflow-hidden bg-white py-16 sm:py-20 lg:py-24">
      <div className="mx-auto w-full max-w-[1240px] px-4 sm:px-8 xl:px-0">
        <div className="mb-8 grid gap-4 sm:mb-10 sm:grid-cols-[1fr_auto] sm:items-end">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6d7d68]">{section.eyebrow || "Lo más elegido"}</p>
            <h2 className="text-[30px] font-semibold leading-tight tracking-[-0.025em] text-[#17233f] sm:text-[42px]">{section.title}</h2>
            <p className="mt-3 max-w-[560px] text-sm leading-6 text-[#6f7480] sm:text-base">
              Favoritos para renovar el dormitorio, el baño y esos pequeños rincones que hacen hogar.
            </p>
          </div>
          <Link
            href={section.ctaHref || "/products"}
            className="inline-flex w-fit items-center gap-3 rounded-full bg-[#17233f] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#b65332]"
          >
            {section.ctaLabel || "Ver todos"}
            <span aria-hidden="true">→</span>
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-x-3.5 gap-y-8 sm:gap-x-5 lg:grid-cols-3 lg:gap-x-6 lg:gap-y-11">
          {items.slice(0, 6).map((item) => <ProductItem item={item} key={item.id} />)}
        </div>
      </div>
    </section>
  );
};

export default BestSeller;
