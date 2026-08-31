import { LoadingBlock } from "../ShopWithSidebar/CatalogLoading";

const ProductLoading = () => (
  <section
    className="relative overflow-hidden bg-white pb-20 pt-5 lg:pt-20 xl:pt-28"
    aria-busy="true"
    aria-label="Cargando producto"
  >
    <div className="mx-auto w-full max-w-[1170px] px-4 sm:px-8 xl:px-0">
      <LoadingBlock className="mb-7 h-3 w-48" />

      <div className="flex flex-col gap-7.5 lg:flex-row xl:gap-17.5">
        <div className="w-full lg:max-w-[570px]">
          <LoadingBlock className="aspect-square w-full rounded-lg" />
          <div className="mt-6 flex gap-4.5 overflow-hidden">
            {Array.from({ length: 4 }).map((_, index) => (
              <LoadingBlock key={index} className="h-15 w-15 shrink-0 rounded-lg sm:h-25 sm:w-25" />
            ))}
          </div>
        </div>

        <div className="w-full max-w-[539px]">
          <div className="mb-4 flex items-start justify-between gap-4">
            <LoadingBlock className="h-8 w-4/5" />
            <LoadingBlock className="h-6 w-14 rounded" />
          </div>
          <LoadingBlock className="mb-5 h-3 w-32" />

          <div className="mb-5 flex gap-5">
            <LoadingBlock className="h-4 w-24" />
            <LoadingBlock className="h-4 w-28" />
          </div>

          <LoadingBlock className="mb-5 h-6 w-40" />
          <div className="mb-7 space-y-2">
            <LoadingBlock className="h-3 w-4/5" />
            <LoadingBlock className="h-3 w-3/5" />
          </div>

          <div className="mb-9 flex flex-col gap-5 border-y border-gray-3 py-9">
            <div className="flex items-center gap-4">
              <LoadingBlock className="h-4 w-16" />
              <div className="flex gap-2.5">
                <LoadingBlock className="h-6 w-6 rounded-full" />
                <LoadingBlock className="h-6 w-6 rounded-full" />
                <LoadingBlock className="h-6 w-6 rounded-full" />
              </div>
            </div>
            <div className="flex items-start gap-4">
              <LoadingBlock className="h-4 w-16" />
              <div className="flex flex-wrap gap-2">
                <LoadingBlock className="h-9 w-16 rounded-md" />
                <LoadingBlock className="h-9 w-20 rounded-md" />
                <LoadingBlock className="h-9 w-16 rounded-md" />
              </div>
            </div>
          </div>

          <LoadingBlock className="mb-5 h-10 w-full max-w-sm rounded-md" />
          <div className="flex gap-3">
            <LoadingBlock className="h-12 w-28 rounded-md" />
            <LoadingBlock className="h-12 w-12 rounded-md" />
          </div>
        </div>
      </div>
    </div>
  </section>
);

export default ProductLoading;
