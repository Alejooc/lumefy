"use client";
import React from "react";
import Breadcrumb from "../Common/Breadcrumb";
import { useAppSelector } from "@/redux/store";
import SingleItem from "./SingleItem";
import { useDispatch } from "react-redux";
import { AppDispatch } from "@/redux/store";
import { removeAllItemsFromWishlist } from "@/redux/features/wishlist-slice";
import Link from "next/link";

export const Wishlist = () => {
  const wishlistItems = useAppSelector((state) => state.wishlistReducer.items);
  const dispatch = useDispatch<AppDispatch>();

  return (
    <>
      <Breadcrumb title={"Favoritos"} pages={["Favoritos"]} />
      <section className="overflow-hidden py-20 bg-gray-2">
        <div className="max-w-[1170px] w-full mx-auto px-4 sm:px-8 xl:px-0">
          <div className="flex flex-wrap items-center justify-between gap-5 mb-7.5">
            <h2 className="font-medium text-dark text-2xl">Tus favoritos</h2>
            <button className="text-blue" onClick={() => dispatch(removeAllItemsFromWishlist())}>
              Vaciar favoritos
            </button>
          </div>
          {wishlistItems.length ? (
            <div className="bg-white rounded-[10px] shadow-1">
              <div className="w-full overflow-x-auto">
                <div className="min-w-[1170px]">
                  <div className="flex items-center py-5.5 px-10">
                    <div className="min-w-[83px]"></div>
                    <div className="min-w-[387px]">
                      <p className="text-dark">Producto</p>
                    </div>
                    <div className="min-w-[205px]">
                      <p className="text-dark">Precio unitario</p>
                    </div>
                    <div className="min-w-[265px]">
                      <p className="text-dark">Estado</p>
                    </div>
                    <div className="min-w-[150px]">
                      <p className="text-dark text-right">Acción</p>
                    </div>
                  </div>
                  {wishlistItems.map((item, key) => (
                    <SingleItem item={item} key={key} />
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-[10px] shadow-1 px-4 py-10 sm:py-15 lg:py-20 text-center">
              <h3 className="font-medium text-dark text-2xl mb-3">Aún no tienes productos guardados</h3>
              <p className="mb-7.5">Guarda tus productos favoritos para revisarlos después.</p>
              <Link
                href="/products"
                className="inline-flex justify-center font-medium text-white bg-blue py-3 px-6 rounded-md ease-out duration-200 hover:bg-blue-dark"
              >
                Seguir comprando
              </Link>
            </div>
          )}
        </div>
      </section>
    </>
  );
};
