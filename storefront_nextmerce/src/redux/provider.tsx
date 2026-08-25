"use client";

import { store } from "./store";
import { Provider } from "react-redux";
import React, { useEffect } from "react";
import { hydrateCart } from "./features/cart-slice";
import { hydrateWishlist } from "./features/wishlist-slice";

const CART_STORAGE_KEY = "nextmerce-cart";
const WISHLIST_STORAGE_KEY = "nextmerce-wishlist";

function scopedStorageKey(baseKey: string): string {
  if (typeof window === "undefined") {
    return baseKey;
  }
  return `${baseKey}:${encodeURIComponent(window.location.host.toLowerCase())}`;
}

export function ReduxProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const cartStorageKey = scopedStorageKey(CART_STORAGE_KEY);
    const wishlistStorageKey = scopedStorageKey(WISHLIST_STORAGE_KEY);
    try {
      const cartRaw = window.localStorage.getItem(cartStorageKey);
      if (cartRaw) {
        const items = JSON.parse(cartRaw);
        if (Array.isArray(items)) {
          store.dispatch(hydrateCart(items));
        }
      }

      const wishlistRaw = window.localStorage.getItem(wishlistStorageKey);
      if (wishlistRaw) {
        const items = JSON.parse(wishlistRaw);
        if (Array.isArray(items)) {
          store.dispatch(hydrateWishlist(items));
        }
      }
    } catch {
      window.localStorage.removeItem(cartStorageKey);
      window.localStorage.removeItem(wishlistStorageKey);
    }

    const unsubscribe = store.subscribe(() => {
      const state = store.getState();
      window.localStorage.setItem(
        cartStorageKey,
        JSON.stringify(state.cartReducer.items),
      );
      window.localStorage.setItem(
        wishlistStorageKey,
        JSON.stringify(state.wishlistReducer.items),
      );
    });

    return () => {
      unsubscribe();
    };
  }, []);

  return <Provider store={store}>{children}</Provider>;
}
