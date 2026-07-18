import { createSelector, createSlice, PayloadAction } from "@reduxjs/toolkit";
import { RootState } from "../store";

type InitialState = {
  items: CartItem[];
};

type CartItem = {
  id: number;
  publishedProductId?: string;
  title: string;
  price: number;
  discountedPrice: number;
  quantity: number;
  href?: string;
  slug?: string;
  inStock?: boolean;
  stockQuantity?: number;
  imgs?: {
    thumbnails: string[];
    previews: string[];
  };
};

const initialState: InitialState = {
  items: [],
};

export const cart = createSlice({
  name: "cart",
  initialState,
  reducers: {
    hydrateCart: (state, action: PayloadAction<CartItem[]>) => {
      state.items = action.payload;
    },
    addItemToCart: (state, action: PayloadAction<CartItem>) => {
      const { id, publishedProductId, title, price, quantity, discountedPrice, imgs, href, slug, inStock, stockQuantity } =
        action.payload;
      if (inStock === false || stockQuantity === 0) {
        return;
      }
      const existingItem = state.items.find((item) => item.id === id);

      if (existingItem) {
        existingItem.quantity = stockQuantity === undefined
          ? existingItem.quantity + quantity
          : Math.min(existingItem.quantity + quantity, stockQuantity);
      } else {
        state.items.push({
          id,
          publishedProductId,
          title,
          price,
          quantity,
          discountedPrice,
          href,
          slug,
          inStock,
          stockQuantity,
          imgs,
        });
      }
    },
    removeItemFromCart: (state, action: PayloadAction<number>) => {
      const itemId = action.payload;
      state.items = state.items.filter((item) => item.id !== itemId);
    },
    updateCartItemQuantity: (
      state,
      action: PayloadAction<{ id: number; quantity: number }>
    ) => {
      const { id, quantity } = action.payload;
      const existingItem = state.items.find((item) => item.id === id);

      if (existingItem) {
        existingItem.quantity = existingItem.stockQuantity === undefined
          ? quantity
          : Math.min(quantity, existingItem.stockQuantity);
      }
    },

    removeAllItemsFromCart: (state) => {
      state.items = [];
    },
  },
});

export const selectCartItems = (state: RootState) => state.cartReducer.items;

export const selectTotalPrice = createSelector([selectCartItems], (items) => {
  return items.reduce((total, item) => {
    return total + item.discountedPrice * item.quantity;
  }, 0);
});

export const {
  hydrateCart,
  addItemToCart,
  removeItemFromCart,
  updateCartItemQuantity,
  removeAllItemsFromCart,
} = cart.actions;
export default cart.reducer;
