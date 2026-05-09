import { createSlice, PayloadAction } from "@reduxjs/toolkit";

type InitialState = {
  items: WishListItem[];
};

type WishListItem = {
  id: number;
  publishedProductId?: string;
  title: string;
  price: number;
  discountedPrice: number;
  quantity: number;
  status?: string;
  href?: string;
  slug?: string;
  description?: string;
  imgs?: {
    thumbnails: string[];
    previews: string[];
  };
};

const initialState: InitialState = {
  items: [],
};

export const wishlist = createSlice({
  name: "wishlist",
  initialState,
  reducers: {
    hydrateWishlist: (state, action: PayloadAction<WishListItem[]>) => {
      state.items = action.payload;
    },
    addItemToWishlist: (state, action: PayloadAction<WishListItem>) => {
      const {
        id,
        publishedProductId,
        title,
        price,
        quantity,
        imgs,
        discountedPrice,
        status,
        href,
        slug,
        description,
      } = action.payload;
      const existingItem = state.items.find((item) => item.id === id);

      if (!existingItem) {
        state.items.push({
          id,
          publishedProductId,
          title,
          price,
          quantity,
          imgs,
          discountedPrice,
          status,
          href,
          slug,
          description,
        });
      }
    },
    removeItemFromWishlist: (state, action: PayloadAction<number>) => {
      const itemId = action.payload;
      state.items = state.items.filter((item) => item.id !== itemId);
    },

    removeAllItemsFromWishlist: (state) => {
      state.items = [];
    },
  },
});

export const {
  hydrateWishlist,
  addItemToWishlist,
  removeItemFromWishlist,
  removeAllItemsFromWishlist,
} = wishlist.actions;
export default wishlist.reducer;
