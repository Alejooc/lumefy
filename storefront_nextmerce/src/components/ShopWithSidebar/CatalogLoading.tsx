export const LoadingBlock = ({ className }: { className: string }) => (
  <div className={`animate-pulse rounded bg-gray-2 ${className}`} aria-hidden="true" />
);

type CatalogLoadingProps = {
  overlay?: boolean;
  variant?: "collection" | "search";
  layout?: "grid" | "list";
};

const CatalogLoading = ({ overlay = false, variant = "collection", layout = "grid" }: CatalogLoadingProps) => {
  const isSearch = variant === "search";
  const cards = layout === "list" ? 4 : 6;

  const content = (
    <section
      className="relative overflow-hidden bg-[#f3f4f6] pb-20 pt-5 lg:pt-20 xl:pt-28"
      aria-busy="true"
      aria-label={isSearch ? "Cargando resultados" : "Cargando colección"}
    >
      <div className="mx-auto w-full max-w-[1170px] px-4 sm:px-8 xl:px-0">
        <LoadingBlock className={`mb-7 h-3 ${isSearch ? "w-40" : "w-24"}`} />

        <div className="flex gap-7.5">
          <aside className="hidden w-[270px] shrink-0 flex-col gap-5 xl:flex">
            <LoadingBlock className="h-14 w-full rounded-lg" />
            <LoadingBlock className="h-72 w-full rounded-lg" />
            <LoadingBlock className="h-56 w-full rounded-lg" />
          </aside>

          <main className="min-w-0 flex-1">
            <div className={`mb-6 rounded-lg bg-white px-6 py-7 shadow-1 sm:px-8 sm:py-9 ${isSearch ? "min-h-[126px]" : "min-h-[166px]"}`}>
              <LoadingBlock className={`mb-3 h-3 ${isSearch ? "w-40" : "w-24"}`} />
              <LoadingBlock className={`h-8 ${isSearch ? "w-3/4 sm:w-2/3" : "w-2/5 sm:w-1/3"}`} />
              {!isSearch ? (
                <div className="mt-4 space-y-2">
                  <LoadingBlock className="h-3 w-11/12 max-w-2xl" />
                  <LoadingBlock className="h-3 w-3/5 max-w-xl" />
                </div>
              ) : null}
            </div>
            <div className="mb-6 flex h-16 items-center justify-between rounded-lg bg-white px-4 shadow-1">
              <div className="flex items-center gap-3">
                <LoadingBlock className="h-9 w-32 rounded-md" />
                <LoadingBlock className="hidden h-3 w-28 sm:block" />
              </div>
              <div className="flex gap-2">
                <LoadingBlock className="h-9 w-10 rounded-md" />
                <LoadingBlock className="h-9 w-10 rounded-md" />
              </div>
            </div>

            <div className={layout === "list" ? "flex flex-col gap-7.5" : "grid grid-cols-2 gap-x-3.5 gap-y-8 sm:gap-x-7.5 sm:gap-y-9 lg:grid-cols-3"}>
              {Array.from({ length: cards }).map((_, index) => (
                <div key={index} className={layout === "list" ? "flex gap-5 rounded-lg bg-white p-4 shadow-1" : "overflow-hidden rounded-lg bg-white shadow-1"}>
                  <LoadingBlock className={layout === "list" ? "h-36 w-36 shrink-0 rounded-md" : "aspect-[4/5] w-full rounded-none"} />
                  <div className={layout === "list" ? "flex flex-1 flex-col justify-center gap-3" : "space-y-3 p-4"}>
                    <LoadingBlock className={layout === "list" ? "h-4 w-2/3" : "h-4 w-4/5"} />
                    <LoadingBlock className={layout === "list" ? "h-3 w-1/3" : "h-3 w-2/5"} />
                    <LoadingBlock className={layout === "list" ? "h-5 w-1/4" : "h-5 w-1/3"} />
                  </div>
                </div>
              ))}
            </div>
          </main>
        </div>
      </div>
    </section>
  );

  return overlay ? (
    <div
      className="fixed inset-0 z-[999999] overflow-y-auto bg-white/90"
      role="status"
      aria-live="polite"
      aria-label="Actualizando catálogo"
    >
      {content}
    </div>
  ) : content;
};

export default CatalogLoading;
