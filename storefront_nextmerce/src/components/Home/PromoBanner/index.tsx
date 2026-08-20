import Image from "next/image";
import Link from "next/link";

import type { HomePromoBanner } from "@/types/home";

const PromoBanner = ({ items }: { items: HomePromoBanner[] }) => {
  if (!items.length) return null;

  return (
    <section className="overflow-hidden bg-white py-16 sm:py-20 lg:py-24">
      <div className="mx-auto w-full max-w-[1240px] px-4 sm:px-8 xl:px-0">
        <div className="mb-8 max-w-[680px]">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#b65332]">Ideas para inspirarte</p>
          <h2 className="text-[30px] font-semibold leading-tight tracking-[-0.025em] text-[#17233f] sm:text-[42px]">
            Pequeños cambios, una casa completamente nueva
          </h2>
        </div>

        <div className={`grid gap-4 sm:gap-5 ${items.length > 1 ? "lg:grid-cols-[1.35fr_0.85fr]" : ""}`}>
          {items.slice(0, 1).map((promo) => (
            <article key={promo.id} className="group relative min-h-[500px] overflow-hidden rounded-[26px] bg-[#17233f] sm:min-h-[600px]">
              <Image
                src={promo.image || "/images/home/home-hero-editorial.webp"}
                alt={promo.title}
                fill
                sizes="(max-width: 1024px) 100vw, 760px"
                className="object-cover transition duration-700 group-hover:scale-[1.035]"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#111827]/90 via-[#111827]/20 to-transparent" />
              <div className="absolute inset-x-0 bottom-0 max-w-[620px] p-6 text-white sm:p-10 lg:p-12">
                {promo.subtitle ? <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-white/75">{promo.subtitle}</p> : null}
                <h3 className="text-[32px] font-semibold leading-[1.08] tracking-[-0.025em] sm:text-[46px]">{promo.title}</h3>
                {promo.description ? <p className="mt-4 max-w-[520px] text-sm leading-7 text-white/85 sm:text-base">{promo.description}</p> : null}
                <Link href={promo.ctaHref} className="mt-6 inline-flex items-center gap-3 rounded-full bg-white px-5 py-3 text-sm font-semibold text-[#17233f] transition hover:bg-[#b65332] hover:text-white">
                  {promo.ctaLabel}<span aria-hidden="true">→</span>
                </Link>
              </div>
            </article>
          ))}

          {items.length > 1 ? (
            <div className="grid gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-1">
              {items.slice(1, 3).map((promo, index) => (
                <Link
                  key={promo.id}
                  href={promo.ctaHref}
                  className="group relative min-h-[310px] overflow-hidden rounded-[24px] bg-[#dde6de] p-6 sm:p-8"
                  style={{ backgroundColor: promo.backgroundColor || (index === 0 ? "#dde6de" : "#eaded2") }}
                >
                  {promo.image ? (
                    <Image
                      src={promo.image}
                      alt={promo.title}
                      fill
                      sizes="(max-width: 1024px) 50vw, 420px"
                      className="object-cover transition duration-700 group-hover:scale-[1.04]"
                    />
                  ) : null}
                  <div className="absolute inset-0 bg-gradient-to-t from-[#111827]/85 via-[#111827]/10 to-transparent" />
                  <div className="absolute inset-x-0 bottom-0 p-6 text-white sm:p-8">
                    {promo.subtitle ? <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/75">{promo.subtitle}</p> : null}
                    <h3 className="text-2xl font-semibold leading-tight">{promo.title}</h3>
                    <span className="mt-4 inline-flex items-center gap-2 text-sm font-semibold">{promo.ctaLabel}<span className="transition group-hover:translate-x-1">→</span></span>
                  </div>
                </Link>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
};

export default PromoBanner;
