"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { selectLastAdded } from "@/redux/features/cart-slice";
import { useAppSelector } from "@/redux/store";

const CartFeedback = () => {
  const lastAdded = useAppSelector(selectLastAdded);
  const [visible, setVisible] = useState(false);
  const seenTimestamp = useRef<number | null>(null);

  useEffect(() => {
    if (!lastAdded || seenTimestamp.current === lastAdded.timestamp) {
      return;
    }

    seenTimestamp.current = lastAdded.timestamp;
    setVisible(true);

    const timeout = window.setTimeout(() => setVisible(false), 4200);
    return () => window.clearTimeout(timeout);
  }, [lastAdded]);

  if (!visible || !lastAdded) {
    return null;
  }

  return (
    <div className="cart-feedback" aria-live="polite" role="status">
      <div key={lastAdded.timestamp} className="cart-feedback__panel">
        <span className="cart-feedback__icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path
              d="M5 12.5 9.5 17 19 7.5"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>

        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-blue-light-3">
            Agregado al carrito
          </p>
          <p className="mt-0.5 truncate text-sm font-medium text-white">
            {lastAdded.title}
          </p>
        </div>

        <Link
          href="/cart"
          className="shrink-0 rounded-lg border border-white/20 px-3 py-2 text-xs font-medium text-white transition hover:border-white hover:bg-white/10"
        >
          Ver carrito
        </Link>
      </div>
    </div>
  );
};

export default CartFeedback;
