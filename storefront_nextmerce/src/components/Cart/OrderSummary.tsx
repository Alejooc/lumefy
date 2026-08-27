"use client";

import { useAppSelector } from "@/redux/store";
import React from "react";
import Link from "next/link";
import { useStorefrontCurrency } from "@/lib/storefront-currency";
import { useStorefrontUi } from "@/lib/storefront-ui";
import type { CartItem } from "@/redux/features/cart-slice";
import type { CartTemplateContent } from "@/lib/cart-template";

type OrderSummaryProps = {
  previewItems?: CartItem[];
  content?: Partial<CartTemplateContent>;
  showItems?: boolean;
  showCheckoutButton?: boolean;
};

const OrderSummary = ({
  previewItems,
  content,
  showItems = true,
  showCheckoutButton = true,
}: OrderSummaryProps) => {
  const storeCartItems = useAppSelector((state) => state.cartReducer.items);
  const cartItems = previewItems ?? storeCartItems;
  const totalPrice = cartItems.reduce(
    (total, item) => total + item.discountedPrice * item.quantity,
    0,
  );
  const { format } = useStorefrontCurrency();
  const { buttonLabels } = useStorefrontUi();

  return (
    <div className="lg:max-w-[455px] w-full">
      <div className="bg-white shadow-1 rounded-[10px]">
        <div className="border-b border-gray-3 py-5 px-4 sm:px-8.5">
          <h3 className="font-medium text-xl text-dark">{content?.summary_title || "Resumen del pedido"}</h3>
        </div>

        <div className="pt-2.5 pb-8.5 px-4 sm:px-8.5">
          {showItems ? (
            <>
              <div className="flex items-center justify-between py-5 border-b border-gray-3">
                <div>
                  <h4 className="font-medium text-dark">{content?.product_label || "Producto"}</h4>
                </div>
                <div>
                  <h4 className="font-medium text-dark text-right">{content?.subtotal_label || "Subtotal"}</h4>
                </div>
              </div>

              {cartItems.map((item, key) => (
                <div key={key} className="flex items-center justify-between py-5 border-b border-gray-3">
                  <div>
                    <p className="text-dark">{item.title}</p>
                  </div>
                  <div>
                    <p className="text-dark text-right">
                      {format(item.discountedPrice * item.quantity)}
                    </p>
                  </div>
                </div>
              ))}
            </>
          ) : null}

          {/* <!-- total --> */}
          <div className="flex items-center justify-between pt-5">
            <div>
              <p className="font-medium text-lg text-dark">{content?.total_label || "Total"}</p>
            </div>
            <div>
              <p className="font-medium text-lg text-dark text-right">
                {format(totalPrice)}
              </p>
            </div>
          </div>

          {/* <!-- checkout button --> */}
          {showCheckoutButton ? (
            <Link
              href="/checkout"
              className="w-full flex justify-center font-medium text-white bg-blue py-3 px-6 rounded-md ease-out duration-200 hover:bg-blue-dark mt-7.5"
            >
              {content?.checkout_label || buttonLabels.goToCheckout}
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default OrderSummary;
