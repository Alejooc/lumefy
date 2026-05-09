import { Menu } from "@/types/Menu";

export const menuData: Menu[] = [
  {
    id: 1,
    title: "Popular",
    newTab: false,
    path: "/",
  },
  {
    id: 2,
    title: "Shop",
    newTab: false,
    path: "/products",
  },
  {
    id: 3,
    title: "Contact",
    newTab: false,
    path: "/contact",
  },
  {
    id: 6,
    title: "pages",
    newTab: false,
    path: "/",
    submenu: [
      {
        id: 61,
        title: "Products",
        newTab: false,
        path: "/products",
      },
      {
        id: 64,
        title: "Checkout",
        newTab: false,
        path: "/checkout",
      },
      {
        id: 65,
        title: "Cart",
        newTab: false,
        path: "/cart",
      },
      {
        id: 66,
        title: "Wishlist",
        newTab: false,
        path: "/wishlist",
      },
      {
        id: 67,
        title: "Login",
        newTab: false,
        path: "/login",
      },
      {
        id: 68,
        title: "Register",
        newTab: false,
        path: "/register",
      },
      {
        id: 69,
        title: "Account",
        newTab: false,
        path: "/account",
      },
      {
        id: 70,
        title: "Contact",
        newTab: false,
        path: "/contact",
      },
    ],
  },
];
