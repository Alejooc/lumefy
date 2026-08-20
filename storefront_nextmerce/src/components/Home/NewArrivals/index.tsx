import Link from "next/link";

import ProductItem from "@/components/Common/ProductItem";
import type { HomeSection } from "@/types/home";
import type { Product } from "@/types/product";

const NewArrival = ({ items, section }: { items: Product[]; section: HomeSection }) => {
  if (!items.length) return null;

  return (
    <section className="overflow-hidden bg-[#f7f4ef] py-16 sm:py-20 lg:py-24">
      <div className="mx-auto w-full max-w-[1240px] px-4 sm:px-8 xl:px-0">
        <div className="mb-8 flex items-end justify-between gap-5 sm:mb-10">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#b65332]">{section.eyebrow || "Recién llegados"}</p>
            <h2 className="text-[30px] font-semibold leading-tight tracking-[-0.025em] text-[#17233f] sm:text-[42px]">{section.title}</h2>
          </div>
          <Link
            href={section.ctaHref || "/products"}
            className="hidden items-center gap-2 border-b border-[#17233f] pb-1 text-sm font-semibold text-[#17233f] transition hover:border-[#b65332] hover:text-[#b65332] sm:inline-flex"
          >
            {section.ctaLabel || "Ver todos"}
            <span aria-hidden="true">→</span>
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-x-3.5 gap-y-8 sm:gap-x-5 lg:grid-cols-4 lg:gap-x-6 lg:gap-y-11">
          {items.slice(0, 8).map((item) => <ProductItem item={item} key={item.id} />)}
        </div>

        <Link
          href={section.ctaHref || "/products"}
          className="mt-9 flex w-full items-center justify-center rounded-full border border-[#17233f] px-5 py-3 text-sm font-semibold text-[#17233f] sm:hidden"
        >
          {section.ctaLabel || "Ver todos"}
        </Link>
      </div>
    </section>
  );
};

export default NewArrival;
