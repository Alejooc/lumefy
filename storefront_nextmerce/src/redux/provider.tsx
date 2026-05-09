"use client";

import { store } from "./store";
import { Provider } from "react-redux";
import React, { useEffect } from "react";
import { hydrateCart } from "./features/cart-slice";
import { hydrateWishlist } from "./features/wishlist-slice";

const CART_STORAGE_KEY = "nextmerce-cart";
const WISHLIST_STORAGE_KEY = "nextmerce-wishlist";

export function ReduxProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    try {
      const cartRaw = window.localStorage.getItem(CART_STORAGE_KEY);
      if (cartRaw) {
        const items = JSON.parse(cartRaw);
        if (Array.isArray(items)) {
          store.dispatch(hydrateCart(items));
        }
      }

      const wishlistRaw = window.localStorage.getItem(WISHLIST_STORAGE_KEY);
      if (wishlistRaw) {
        const items = JSON.parse(wishlistRaw);
        if (Array.isArray(items)) {
          store.dispatch(hydrateWishlist(items));
        }
      }
    } catch {
      window.localStorage.removeItem(CART_STORAGE_KEY);
      window.localStorage.removeItem(WISHLIST_STORAGE_KEY);
    }

    const unsubscribe = store.subscribe(() => {
      const state = store.getState();
      window.localStorage.setItem(
        CART_STORAGE_KEY,
        JSON.stringify(state.cartReducer.items),
      );
      window.localStorage.setItem(
        WISHLIST_STORAGE_KEY,
        JSON.stringify(state.wishlistReducer.items),
      );
    });

    return () => {
      unsubscribe();
    };
  }, []);

  return <Provider store={store}>{children}</Provider>;
}
