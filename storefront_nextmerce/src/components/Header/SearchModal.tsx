"use client";

import React, { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  getPublicCollections,
  getPublicProducts,
  resolveStorefront,
} from "@/lib/storefront-api";
import { storefrontImageUrl } from "@/lib/storefront-image";
import { PublicCatalogFacet, PublicCollection, PublicProduct } from "@/types/storefront";

type SearchModalProps = {
  isOpen: boolean;
  initialQuery?: string;
  collectionSlug?: string;
  onClose: () => void;
};

type SearchProductResult = {
  id: string;
  title: string;
  slug: string;
  description: string;
  imageUrl: string;
  collectionNames: string[];
  brandName: string;
};

const RECENT_SEARCHES_KEY = "storefront_recent_searches";

function stripHtml(value?: string | null): string {
  return (value || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function fallbackImage(seed: string): string {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) | 0;
  }
  return `/images/products/product-${(Math.abs(hash) % 8) + 1}-bg-1.png`;
}

function highlightText(text: string, query: string): React.ReactNode {
  const normalized = query.trim();
  if (!normalized) {
    return text;
  }

  const escaped = normalized.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(`(${escaped})`, "ig");
  const parts = text.split(pattern);
  const lowerQuery = normalized.toLowerCase();

  return parts.map((part, index) =>
    part.toLowerCase() === lowerQuery ? (
      <mark key={`${part}-${index}`} className="rounded bg-blue/10 px-0.5 text-blue">
        {part}
      </mark>
    ) : (
      <React.Fragment key={`${part}-${index}`}>{part}</React.Fragment>
    ),
  );
}

function normalizeSearchValue(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export default function SearchModal({
  isOpen,
  initialQuery = "",
  collectionSlug,
  onClose,
}: SearchModalProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);
  const [collections, setCollections] = useState<PublicCollection[]>([]);
  const [catalogProducts, setCatalogProducts] = useState<PublicProduct[]>([]);
  const [catalogBrands, setCatalogBrands] = useState<PublicCatalogFacet[]>([]);
  const [loading, setLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    setQuery(initialQuery);
    setDebouncedQuery(initialQuery);
  }, [initialQuery, isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    try {
      const stored = window.localStorage.getItem(RECENT_SEARCHES_KEY);
      if (!stored) {
        setRecentSearches([]);
        return;
      }

      const parsed = JSON.parse(stored) as unknown;
      if (Array.isArray(parsed)) {
        setRecentSearches(parsed.filter((item): item is string => typeof item === "string").slice(0, 6));
      }
    } catch {
      setRecentSearches([]);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || collections.length) {
      return;
    }

    let active = true;
    setLoading(true);

    async function loadCollections() {
      try {
        const storefront = await resolveStorefront();
        const collections = await getPublicCollections(storefront.id);
        if (active) {
          setCollections(collections);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadCollections();

    return () => {
      active = false;
    };
  }, [collections.length, isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const timeout = window.setTimeout(() => {
      setDebouncedQuery(query);
    }, 180);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [isOpen, query]);

  const normalizedQuery = normalizeSearchValue(debouncedQuery);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    let active = true;
    setLoading(true);

    async function loadCatalogSearch() {
      try {
        const storefront = await resolveStorefront();
        const catalog = await getPublicProducts(storefront.id, {
          q: debouncedQuery.trim() || undefined,
          page_size: 8,
          sort: "latest",
        });
        if (active) {
          setCatalogProducts(catalog.items);
          setCatalogBrands(catalog.brands);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadCatalogSearch();
    return () => {
      active = false;
    };
  }, [debouncedQuery, isOpen]);

  const productResults = useMemo<SearchProductResult[]>(() => {
    return catalogProducts.map((product) => ({
      id: product.id,
      title: product.title,
      slug: product.slug,
      description: stripHtml(product.description),
      imageUrl: storefrontImageUrl(product.image_url) || storefrontImageUrl(product.gallery?.[0]) || fallbackImage(product.slug),
      collectionNames: [],
      brandName: product.brand_name || "",
    }));
  }, [catalogProducts]);

  const categorySuggestions = useMemo(() => {
    if (!normalizedQuery) {
      return (collectionSlug
        ? collections.filter((collection) => collection.slug === collectionSlug)
        : collections
      ).slice(0, 6);
    }

    return (collectionSlug
      ? collections.filter((collection) => collection.slug === collectionSlug)
      : collections
    )
      .filter((collection) => {
        const inCollectionName = normalizeSearchValue(collection.name).includes(normalizedQuery);
        const inProducts = (collection.products || []).some((product) =>
          normalizeSearchValue(
            `${product.title} ${product.slug} ${product.brand_name || ""} ${stripHtml(product.description)}`,
          ).includes(normalizedQuery),
        );
        return inCollectionName || inProducts;
      })
      .slice(0, 6);
  }, [collectionSlug, collections, normalizedQuery]);

  const trendingCollections = useMemo(
    () => collections.filter((collection) => collection.is_featured).slice(0, 4),
    [collections],
  );

  const brandSuggestions = useMemo(() => {
    const items = catalogBrands
      .map((brand) => ({ name: brand.value, products: brand.products }))
      .sort((left, right) => right.products - left.products);

    if (!normalizedQuery) {
      return items.slice(0, 6);
    }

    return items
      .filter((item) => normalizeSearchValue(item.name).includes(normalizedQuery))
      .slice(0, 6);
  }, [catalogBrands, normalizedQuery]);

  const buildProductsSearchUrl = (value: string) => {
    const params = new URLSearchParams();
    const trimmed = value.trim();
    const shouldPreserveFilters = pathname === "/products";

    if (shouldPreserveFilters) {
      ["collection", "category", "brand", "type", "size", "color", "sort", "minPrice", "maxPrice"].forEach((key) => {
        const current = searchParams.get(key);
        if (current) {
          params.set(key, current);
        }
      });
    }

    if (trimmed) {
      params.set("q", trimmed);
    }

    return params.toString() ? `/products?${params.toString()}` : "/products";
  };

  const saveRecentSearch = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }

    const next = [trimmed, ...recentSearches.filter((item) => item.toLowerCase() !== trimmed.toLowerCase())].slice(0, 6);
    setRecentSearches(next);
    window.localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next));
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    saveRecentSearch(trimmed);
    onClose();
    router.push(buildProductsSearchUrl(trimmed));
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[100000] overflow-y-auto bg-dark/70 px-3 py-3 sm:px-5 sm:py-6" onClick={onClose}>
      <div
        className="mx-auto flex min-h-[calc(100vh-24px)] max-w-[1040px] flex-col rounded-[20px] bg-white shadow-1 sm:min-h-[calc(100vh-48px)]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-4 border-b border-gray-3 px-5 py-5 sm:px-8">
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-[0.2em] text-dark-4">
              Buscar productos
            </p>
            <h2 className="text-xl font-semibold text-dark sm:text-2xl">
              Encuentra productos, colecciones y marcas
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar buscador"
            className="flex h-11 w-11 items-center justify-center rounded-full border border-gray-3 text-dark transition hover:border-blue hover:text-blue"
          >
            <svg className="fill-current" width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M5.28 4.22 10 8.94l4.72-4.72 1.06 1.06L11.06 10l4.72 4.72-1.06 1.06L10 11.06l-4.72 4.72-1.06-1.06L8.94 10 4.22 5.28l1.06-1.06Z" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-8 sm:py-7">
          <form onSubmit={handleSubmit} className="relative mb-7">
            <input
              autoFocus
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Busca por producto, coleccion o palabra clave"
              className="w-full rounded-xl border border-gray-3 bg-gray-1 py-4 pl-4 pr-4 text-dark outline-none transition focus:border-blue focus:bg-white sm:pl-5 sm:pr-36"
            />

            <button
              type="submit"
              className="mt-3 inline-flex w-full items-center justify-center rounded-lg bg-blue px-5 py-3 font-medium text-white transition hover:bg-blue-dark sm:absolute sm:right-2 sm:top-1/2 sm:mt-0 sm:w-auto sm:-translate-y-1/2"
            >
              Buscar
            </button>
          </form>

          {!normalizedQuery ? (
            <div className="mb-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <div className="rounded-2xl bg-gray-1 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-base font-semibold text-dark">Busquedas recientes</h3>
                  {recentSearches.length ? (
                    <button
                      type="button"
                      onClick={() => {
                        setRecentSearches([]);
                        window.localStorage.removeItem(RECENT_SEARCHES_KEY);
                      }}
                      className="text-sm text-dark-4 transition hover:text-blue"
                    >
                      Limpiar
                    </button>
                  ) : null}
                </div>

                <div className="flex flex-wrap gap-2.5">
                  {recentSearches.length ? (
                    recentSearches.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => {
                          setQuery(item);
                          setDebouncedQuery(item);
                        }}
                        className="rounded-full border border-gray-3 bg-white px-3 py-2 text-sm text-dark transition hover:border-blue hover:text-blue"
                      >
                        {item}
                      </button>
                    ))
                  ) : (
                    <p className="text-sm text-dark-4">Aun no tienes busquedas recientes.</p>
                  )}
                </div>
              </div>

              <div className="rounded-2xl bg-gray-1 p-4">
                <h3 className="mb-3 text-base font-semibold text-dark">Colecciones destacadas</h3>
                <div className="flex flex-wrap gap-2.5">
                  {(trendingCollections.length ? trendingCollections : collections.slice(0, 4)).map((collection) => (
                    <Link
                      key={collection.id}
                      href={`/products?collection=${encodeURIComponent(collection.slug)}`}
                      onClick={onClose}
                      className="rounded-full border border-gray-3 bg-white px-3 py-2 text-sm text-dark transition hover:border-blue hover:text-blue"
                    >
                      {collection.name}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          <div className="grid gap-7 lg:grid-cols-[minmax(0,2fr)_320px]">
            <div>
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-dark">
                  {normalizedQuery ? "Resultados sugeridos" : "Productos destacados"}
                </h3>
                {!loading ? (
                  <span className="text-sm text-dark-4">
                    {productResults.length} resultado{productResults.length === 1 ? "" : "s"}
                  </span>
                ) : null}
              </div>

              {loading ? (
                <div className="rounded-2xl border border-gray-3 bg-gray-1 px-5 py-8 text-sm text-dark-4">
                  Cargando sugerencias...
                </div>
              ) : productResults.length ? (
                <div className="grid gap-4 sm:grid-cols-2">
                  {productResults.map((item) => (
                    <Link
                      key={item.id}
                      href={`/products/${encodeURIComponent(item.slug)}`}
                      onClick={onClose}
                      className="group flex gap-4 rounded-2xl border border-gray-3 bg-white p-3 transition hover:border-blue hover:shadow-1"
                    >
                      <div className="relative h-24 w-24 flex-shrink-0 overflow-hidden rounded-xl bg-gray-1">
                        <Image
                          src={item.imageUrl}
                          alt={item.title}
                          fill
                          className="object-cover transition duration-300 group-hover:scale-105"
                        />
                      </div>

                      <div className="min-w-0">
                        <p className="mb-1 text-xs font-medium uppercase tracking-[0.18em] text-blue">
                          {highlightText(item.collectionNames[0] || "Producto", debouncedQuery)}
                        </p>
                        <h4 className="mb-1 line-clamp-2 font-medium text-dark">
                          {highlightText(item.title, debouncedQuery)}
                        </h4>
                        {item.brandName ? (
                          <p className="mb-1 text-xs text-dark-4">
                            Marca: {highlightText(item.brandName, debouncedQuery)}
                          </p>
                        ) : null}
                        <p className="line-clamp-2 text-sm text-dark-4">
                          {highlightText(item.description || "Descubre mas detalles de este producto.", debouncedQuery)}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-gray-3 bg-gray-1 px-5 py-8">
                  <h4 className="mb-2 text-lg font-medium text-dark">No encontramos coincidencias</h4>
                  <p className="mb-5 text-sm text-dark-4">
                    Prueba con otra palabra clave, revisa una marca sugerida o explora nuestras colecciones destacadas.
                  </p>

                  <div className="flex flex-wrap gap-2.5">
                    {brandSuggestions.slice(0, 4).map((brand) => (
                      <button
                        key={brand.name}
                        type="button"
                        onClick={() => {
                          setQuery(brand.name);
                          setDebouncedQuery(brand.name);
                        }}
                        className="rounded-full border border-gray-3 bg-white px-3 py-2 text-sm text-dark transition hover:border-blue hover:text-blue"
                      >
                        {brand.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <aside className="rounded-2xl bg-gray-1 p-5">
              <h3 className="mb-4 text-lg font-semibold text-dark">Colecciones sugeridas</h3>

              <div className="flex flex-col gap-3">
                {categorySuggestions.length ? (
                  categorySuggestions.map((collection) => (
                    <Link
                      key={collection.id}
                      href={`/products?collection=${encodeURIComponent(collection.slug)}`}
                      onClick={onClose}
                      className="flex items-center justify-between rounded-xl border border-transparent bg-white px-4 py-3 text-sm text-dark transition hover:border-blue hover:text-blue"
                    >
                      <span>{highlightText(collection.name, debouncedQuery)}</span>
                      <span className="rounded-full bg-gray-1 px-2 py-1 text-xs text-dark-4">
                        {collection.products?.length || 0}
                      </span>
                    </Link>
                  ))
                ) : (
                  <p className="text-sm text-dark-4">Aun no hay colecciones sugeridas.</p>
                )}
              </div>

              <div className="mt-6 rounded-2xl bg-white p-4">
                <p className="mb-2 text-sm font-medium text-dark">Marcas sugeridas</p>
                <div className="mb-4 flex flex-wrap gap-2">
                  {brandSuggestions.length ? (
                    brandSuggestions.map((brand) => (
                      <button
                        key={brand.name}
                        type="button"
                        onClick={() => {
                          setQuery(brand.name);
                          setDebouncedQuery(brand.name);
                        }}
                        className="rounded-full border border-gray-3 px-3 py-2 text-sm text-dark transition hover:border-blue hover:text-blue"
                      >
                        {highlightText(brand.name, debouncedQuery)}
                      </button>
                    ))
                  ) : (
                    <p className="text-sm text-dark-4">Aun no hay marcas destacadas.</p>
                  )}
                </div>
              </div>

              <div className="mt-6 rounded-2xl bg-white p-4">
                <p className="mb-2 text-sm font-medium text-dark">Ir a una busqueda completa</p>
                <p className="mb-4 text-sm text-dark-4">
                  Usa la busqueda avanzada para combinar categorias, tallas, colores y precio.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    saveRecentSearch(query);
                    onClose();
                    router.push(buildProductsSearchUrl(query));
                  }}
                  className="inline-flex rounded-lg bg-dark px-4 py-3 text-sm font-medium text-white transition hover:bg-blue"
                >
                  Ver todos los resultados
                </button>
              </div>
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}
