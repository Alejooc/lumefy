import { configureStore, type Middleware } from "@reduxjs/toolkit";

import quickViewReducer from "./features/quickView-slice";
import cartReducer, {
  addItemToCart,
  removeItemFromCart,
  type CartItem,
  updateCartItemQuantity,
} from "./features/cart-slice";
import wishlistReducer from "./features/wishlist-slice";
import productDetailsReducer from "./features/product-details";

import { TypedUseSelectorHook, useSelector } from "react-redux";
import { trackStorefrontEvent, trackingItem } from "@/lib/storefront-tracking";

type CartStateShape = {
  cartReducer: {
    items: CartItem[];
  };
};

const storefrontTrackingMiddleware: Middleware = (api) => (next) => (action) => {
  const beforeItems = (api.getState() as CartStateShape).cartReducer.items;
  const result = next(action);
  const afterItems = (api.getState() as CartStateShape).cartReducer.items;

  if (addItemToCart.match(action)) {
    const previousQuantity = beforeItems.find((item) => item.id === action.payload.id)?.quantity || 0;
    const item = afterItems.find((candidate) => candidate.id === action.payload.id);
    const quantityAdded = item ? item.quantity - previousQuantity : 0;
    if (item && quantityAdded > 0) {
      trackStorefrontEvent({
        name: "add_to_cart",
        value: item.discountedPrice * quantityAdded,
        items: [trackingItem({ ...item, quantity: quantityAdded })],
      });
    }
  }

  if (removeItemFromCart.match(action)) {
    const removed = beforeItems.find((item) => item.id === action.payload);
    if (removed) {
      trackStorefrontEvent({
        name: "remove_from_cart",
        value: removed.discountedPrice * removed.quantity,
        items: [trackingItem(removed)],
      });
    }
  }

  if (updateCartItemQuantity.match(action)) {
    const previous = beforeItems.find((item) => item.id === action.payload.id);
    const current = afterItems.find((item) => item.id === action.payload.id);
    if (previous && current && previous.quantity !== current.quantity) {
      const quantityDelta = current.quantity - previous.quantity;
      trackStorefrontEvent({
        name: quantityDelta > 0 ? "add_to_cart" : "remove_from_cart",
        value: current.discountedPrice * Math.abs(quantityDelta),
        items: [trackingItem({ ...current, quantity: Math.abs(quantityDelta) })],
      });
    }
  }

  return result;
};

export const store = configureStore({
  reducer: {
    quickViewReducer,
    cartReducer,
    wishlistReducer,
    productDetailsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(storefrontTrackingMiddleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
