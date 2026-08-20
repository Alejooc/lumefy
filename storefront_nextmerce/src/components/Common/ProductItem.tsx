"use client";

import Image from "next/image";
import Link from "next/link";
import { useDispatch } from "react-redux";

import { useModalContext } from "@/app/context/QuickViewModalContext";
import { useStorefrontAuth } from "@/lib/storefront-auth";
import { useStorefrontCurrency } from "@/lib/storefront-currency";
import { addItemToCart } from "@/redux/features/cart-slice";
import { updateproductDetails } from "@/redux/features/product-details";
import { updateQuickView } from "@/redux/features/quickView-slice";
import { addItemToWishlist } from "@/redux/features/wishlist-slice";
import type { AppDispatch } from "@/redux/store";
import type { Product } from "@/types/product";

const ProductItem = ({ item }: { item: Product }) => {
  const { openModal } = useModalContext();
  const { format } = useStorefrontCurrency();
  const { session, loading: authLoading } = useStorefrontAuth();
  const dispatch = useDispatch<AppDispatch>();
  const hasVariants = Boolean(item.variants?.length);
  const productHref = item.href || "/products";

  const rememberProduct = () => dispatch(updateproductDetails({ ...item }));
  const openQuickView = () => {
    dispatch(updateQuickView({ ...item }));
    openModal();
  };
  const addToWishlist = () => {
    if (!session) return;
    dispatch(addItemToWishlist({ ...item, status: "available", quantity: 1 }));
  };
  const addToCart = () => {
    if (hasVariants || item.inStock === false) return;
    dispatch(addItemToCart({ ...item, quantity: 1 }));
  };

  return (
    <article className="group min-w-0">
      <div className="relative mb-4 aspect-[4/5] overflow-hidden rounded-[18px] bg-[#f2efe9]">
        <Link href={productHref} onClick={rememberProduct} aria-label={`Ver ${item.title}`} className="absolute inset-0">
          <Image
            src={item.imgs?.previews?.[0] || "/images/home/home-hero-editorial.webp"}
            alt={item.title}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 300px"
            className="object-cover transition duration-700 group-hover:scale-[1.035]"
          />
        </Link>

        {item.price > item.discountedPrice ? (
          <span className="absolute left-3 top-3 rounded-full bg-[#b65332] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-white">
            Oferta
          </span>
        ) : null}

        <div className="absolute right-3 top-3 flex flex-col gap-2 opacity-100 transition sm:translate-x-3 sm:opacity-0 sm:group-hover:translate-x-0 sm:group-hover:opacity-100">
          <button
            type="button"
            onClick={openQuickView}
            aria-label="Vista rápida"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-[#17233f] shadow-[0_6px_20px_rgba(15,23,42,.14)] transition hover:bg-[#17233f] hover:text-white"
          >
            <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true">
              <path d="M1.8 8.5s2.45-4 6.7-4 6.7 4 6.7 4-2.45 4-6.7 4-6.7-4-6.7-4Z" stroke="currentColor" strokeWidth="1.35" />
              <circle cx="8.5" cy="8.5" r="2" stroke="currentColor" strokeWidth="1.35" />
            </svg>
          </button>
          <button
            type="button"
            onClick={addToWishlist}
            aria-label={session ? "Agregar a favoritos" : "Inicia sesión para guardar favoritos"}
            title={session ? "Agregar a favoritos" : "Inicia sesión para guardar favoritos"}
            disabled={!session || authLoading}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-[#17233f] shadow-[0_6px_20px_rgba(15,23,42,.14)] transition hover:bg-[#b65332] hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true">
              <path d="M8.5 14.2 3.1 9.1a3.45 3.45 0 0 1 4.88-4.88l.52.52.52-.52A3.45 3.45 0 1 1 13.9 9.1l-5.4 5.1Z" stroke="currentColor" strokeWidth="1.35" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        <div className="absolute inset-x-3 bottom-3 translate-y-0 transition sm:translate-y-16 sm:group-hover:translate-y-0">
          {hasVariants ? (
            <Link
              href={productHref}
              onClick={rememberProduct}
              className="flex w-full items-center justify-center rounded-full bg-[#17233f] px-4 py-3 text-sm font-semibold text-white shadow-[0_8px_28px_rgba(15,23,42,.2)] transition hover:bg-[#b65332]"
            >
              Elegir opciones
            </Link>
          ) : (
            <button
              type="button"
              onClick={addToCart}
              disabled={item.inStock === false}
              className="flex w-full items-center justify-center rounded-full bg-[#17233f] px-4 py-3 text-sm font-semibold text-white shadow-[0_8px_28px_rgba(15,23,42,.2)] transition hover:bg-[#b65332] disabled:cursor-not-allowed disabled:bg-[#7d8491]"
            >
              {item.inStock === false ? "Agotado" : "Agregar al carrito"}
            </button>
          )}
        </div>
      </div>

      {item.categoryName ? (
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9b7662]">{item.categoryName}</p>
      ) : null}
      <h3 className="line-clamp-2 min-h-[44px] text-[15px] font-medium leading-[22px] text-[#17233f] transition group-hover:text-[#b65332]">
        <Link href={productHref} onClick={rememberProduct}>{item.title}</Link>
      </h3>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-base font-semibold">
        <span className="text-[#17233f]">{format(item.discountedPrice)}</span>
        {item.price > item.discountedPrice ? <span className="text-sm font-normal text-[#969aa4] line-through">{format(item.price)}</span> : null}
      </div>
    </article>
  );
};

export default ProductItem;
