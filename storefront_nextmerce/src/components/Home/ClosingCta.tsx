import Link from "next/link";

const ClosingCta = ({ storeName }: { storeName: string }) => (
  <section className="overflow-hidden bg-[#f4f0e9] py-16 sm:py-20">
    <div className="mx-auto w-full max-w-[1240px] px-4 sm:px-8 xl:px-0">
      <div className="relative overflow-hidden rounded-[28px] bg-[#b65332] px-6 py-12 text-white sm:px-10 sm:py-16 lg:px-16">
        <div className="absolute -right-20 -top-32 h-80 w-80 rounded-full border-[55px] border-white/[0.07]" />
        <div className="absolute -bottom-28 right-[22%] h-64 w-64 rounded-full bg-[#17233f]/15 blur-2xl" />
        <div className="relative z-10 grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end">
          <div className="max-w-[720px]">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-white/70">Estamos para ayudarte</p>
            <h2 className="text-[32px] font-semibold leading-[1.08] tracking-[-0.025em] sm:text-[46px]">
              Encuentra eso que hará sentir tu casa aún más tuya
            </h2>
            <p className="mt-4 max-w-[590px] text-sm leading-7 text-white/80 sm:text-base">
              Explora el catálogo de {storeName} o escríbenos si necesitas ayuda para elegir medidas, colores o combinaciones.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link href="/products" className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3.5 text-sm font-semibold text-[#17233f] transition hover:-translate-y-0.5">
              Ver catálogo
            </Link>
            <Link href="/contact" className="inline-flex items-center justify-center rounded-full border border-white/40 px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-white hover:text-[#17233f]">
              Hablar con nosotros
            </Link>
          </div>
        </div>
      </div>
    </div>
  </section>
);

export default ClosingCta;
