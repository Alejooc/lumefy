# NextMerce Integration Plan

## Current Status

- Base project created in `storefront_nextmerce`
- Dependencies installed
- Production build passes
- Lint passes

## Main Mock/Data Sources To Replace

- `src/components/Shop/shopData.ts`
- `src/components/Home/Categories/categoryData.ts`
- `src/components/Home/Testimonials/testimonialsData.ts`
- `src/components/Orders/ordersData.tsx`
- `src/components/Header/menuData.ts`

## Main State/Behavior To Replace

- Redux cart: `src/redux/features/cart-slice.ts`
- Redux wishlist: `src/redux/features/wishlist-slice.ts`
- Quick view modal state
- Product details state

## First Backend Integration Targets

1. Home page:
   - replace `shopData` and category mock data with published storefront products and collections
2. Shop pages:
   - map product listing and filters to backend storefront endpoints
3. Product detail:
   - load a real product by slug
4. Cart:
   - decide whether to keep local cart first or reuse current Lumefy cart provider logic
5. Checkout:
   - wire to preview, create order and payment intent endpoints from FastAPI

## Recommended Order

1. Create a thin API client for FastAPI storefront endpoints
2. Create adapters from backend payloads to NextMerce `Product` and `Category` UI shapes
3. Replace home/shop/product detail mock data first
4. Replace cart state
5. Replace checkout flow

## Notes

- `storefront_next` remains available as reference for the existing backend contract
- The new work should happen in `storefront_nextmerce`
