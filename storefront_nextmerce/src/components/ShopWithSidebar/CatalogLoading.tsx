const LoadingBlock = ({ className }: { className: string }) => (
  <div className={`animate-pulse rounded bg-gray-2 ${className}`} aria-hidden="true" />
);

type CatalogLoadingProps = {
  overlay?: boolean;
};

const CatalogLoading = ({ overlay = false }: CatalogLoadingProps) => {
  const content = (
    <section
      className="relative overflow-hidden bg-[#f3f4f6] pb-20 pt-5 lg:pt-20 xl:pt-28"
      aria-busy="true"
      aria-label="Cargando catálogo"
    >
      <div className="mx-auto w-full max-w-[1170px] px-4 sm:px-8 xl:px-0">
        <LoadingBlock className="mb-7 h-3 w-24" />

        <div className="flex gap-7.5">
          <aside className="hidden w-[270px] shrink-0 flex-col gap-5 xl:flex">
            <LoadingBlock className="h-14 w-full rounded-lg" />
            <LoadingBlock className="h-72 w-full rounded-lg" />
            <LoadingBlock className="h-56 w-full rounded-lg" />
          </aside>

          <main className="min-w-0 flex-1">
            <LoadingBlock className="mb-6 h-36 w-full rounded-lg sm:h-44" />
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

            <div className="grid grid-cols-2 gap-x-3.5 gap-y-8 sm:gap-x-7.5 sm:gap-y-9 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div key={index} className="overflow-hidden rounded-lg bg-white shadow-1">
                  <LoadingBlock className="aspect-[4/5] w-full rounded-none" />
                  <div className="space-y-3 p-4">
                    <LoadingBlock className="h-4 w-4/5" />
                    <LoadingBlock className="h-3 w-2/5" />
                    <LoadingBlock className="h-5 w-1/3" />
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
