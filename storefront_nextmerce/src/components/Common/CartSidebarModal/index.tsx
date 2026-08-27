"use client";
import React, { useEffect, useState } from "react";

import { useCartModalContext } from "@/app/context/CartSidebarModalContext";
import {
  removeItemFromCart,
  selectTotalPrice,
} from "@/redux/features/cart-slice";
import { useAppSelector } from "@/redux/store";
import { useSelector } from "react-redux";
import SingleItem from "./SingleItem";
import Link from "next/link";
import EmptyCart from "./EmptyCart";
import { useStorefrontCurrency } from "@/lib/storefront-currency";
import { useStorefrontUi } from "@/lib/storefront-ui";

const CartSidebarModal = () => {
  const { isCartModalOpen, closeCartModal } = useCartModalContext();
  const cartItems = useAppSelector((state) => state.cartReducer.items);
  const { format } = useStorefrontCurrency();
  const { buttonLabels } = useStorefrontUi();

  const totalPrice = useSelector(selectTotalPrice);

  useEffect(() => {
    // closing modal while clicking outside
    function handleClickOutside(event) {
      if (event.target instanceof Element && !event.target.closest(".modal-content")) {
        closeCartModal();
      }
    }

    if (isCartModalOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isCartModalOpen, closeCartModal]);

  return (
    <div
      className={`fixed inset-0 z-99999 overflow-hidden bg-dark/70 transition-[opacity,visibility,transform] duration-300 ease-out ${
        isCartModalOpen
          ? "visible translate-x-0 opacity-100 pointer-events-auto"
          : "invisible translate-x-full opacity-0 pointer-events-none"
      }`}
      aria-hidden={!isCartModalOpen}
      role="dialog"
      aria-modal="true"
      aria-label="Carrito de compras"
    >
      <div className="flex h-full items-center justify-end">
        <div className="modal-content flex h-full w-full max-w-[500px] flex-col bg-white px-4 shadow-1 sm:px-7.5 lg:px-11">
          <div className="flex shrink-0 items-center justify-between border-b border-gray-3 bg-white pb-5 pt-4 sm:pb-7 sm:pt-7.5 lg:pb-7 lg:pt-11">
            <h2 className="font-medium text-dark text-lg sm:text-2xl">
              Mi carrito
            </h2>
            <button
              onClick={() => closeCartModal()}
              aria-label="button for close modal"
              className="flex items-center justify-center ease-in duration-150 bg-meta text-dark-5 hover:text-dark"
            >
              <svg
                className="fill-current"
                width="30"
                height="30"
                viewBox="0 0 30 30"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M12.5379 11.2121C12.1718 10.846 11.5782 10.846 11.212 11.2121C10.8459 11.5782 10.8459 12.1718 11.212 12.5379L13.6741 15L11.2121 17.4621C10.846 17.8282 10.846 18.4218 11.2121 18.7879C11.5782 19.154 12.1718 19.154 12.5379 18.7879L15 16.3258L17.462 18.7879C17.8281 19.154 18.4217 19.154 18.7878 18.7879C19.154 18.4218 19.154 17.8282 18.7878 17.462L16.3258 15L18.7879 12.5379C19.154 12.1718 19.154 11.5782 18.7879 11.2121C18.4218 10.846 17.8282 10.846 17.462 11.2121L15 13.6742L12.5379 11.2121Z"
                  fill=""
                />
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M15 1.5625C7.57867 1.5625 1.5625 7.57867 1.5625 15C1.5625 22.4213 7.57867 28.4375 15 28.4375C22.4213 28.4375 28.4375 22.4213 28.4375 15C28.4375 7.57867 22.4213 1.5625 15 1.5625ZM3.4375 15C3.4375 8.61421 8.61421 3.4375 15 3.4375C21.3858 3.4375 26.5625 8.61421 26.5625 15C26.5625 21.3858 21.3858 26.5625 15 26.5625C8.61421 26.5625 3.4375 21.3858 3.4375 15Z"
                  fill=""
                />
              </svg>
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto py-6 no-scrollbar sm:py-7.5">
            <div className="flex flex-col gap-6">
              {/* <!-- cart item --> */}
              {cartItems.length > 0 ? (
                cartItems.map((item, key) => (
                  <SingleItem
                    key={key}
                    item={item}
                    removeItemFromCart={removeItemFromCart}
                  />
                ))
              ) : (
                <EmptyCart />
              )}
            </div>
          </div>

          <div className="mt-auto shrink-0 border-t border-gray-3 bg-white pb-4 pt-5 sm:pb-7.5 lg:pb-11">
            <div className="mb-5 flex items-center justify-between gap-5 sm:mb-6">
              <p className="font-medium text-xl text-dark">Subtotal:</p>

              <p className="font-medium text-xl text-dark">{format(totalPrice)}</p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
              <Link
                onClick={() => closeCartModal()}
                href="/cart"
                className="flex min-h-11 min-w-0 flex-1 items-center justify-center rounded-md bg-blue px-3 py-3 text-center text-sm font-medium leading-5 text-white ease-out duration-200 hover:bg-blue-dark sm:px-6"
              >
                {buttonLabels.viewCart}
              </Link>

              <Link
                onClick={() => closeCartModal()}
                href="/checkout"
                className="flex min-h-11 min-w-0 flex-1 items-center justify-center rounded-md bg-dark px-3 py-3 text-center text-sm font-medium leading-5 text-white ease-out duration-200 hover:bg-opacity-95 sm:px-6"
              >
                {buttonLabels.goToCheckout}
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CartSidebarModal;
