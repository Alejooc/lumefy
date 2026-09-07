"use client";

import type { CSSProperties } from "react";
import { useEffect, useState } from "react";
import { useStorefrontCurrency } from "@/lib/storefront-currency";
import { useStorefrontUi } from "@/lib/storefront-ui";

type PriceRangeStyle = CSSProperties & {
  "--price-range-start": string;
  "--price-range-end": string;
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

const PriceDropdown = ({
  min,
  max,
  selectedMin,
  selectedMax,
  onApply,
}: {
  min: number;
  max: number;
  selectedMin: number;
  selectedMax: number;
  onApply: (minValue: number, maxValue: number) => void;
}) => {
  const [toggleDropdown, setToggleDropdown] = useState(true);
  const safeMin = Number.isFinite(min) ? min : 0;
  const safeMax = Math.max(Number.isFinite(max) ? max : safeMin + 1, safeMin + 1);
  const [range, setRange] = useState<[number, number]>([
    clamp(selectedMin, safeMin, safeMax),
    clamp(selectedMax || max, safeMin, safeMax),
  ]);
  const { format } = useStorefrontCurrency();
  const { buttonLabels } = useStorefrontUi();

  useEffect(() => {
    const nextMin = clamp(selectedMin, safeMin, safeMax);
    const nextMax = clamp(selectedMax || max, nextMin, safeMax);
    setRange([nextMin, nextMax]);
  }, [max, safeMax, safeMin, selectedMax, selectedMin]);

  const rangeStart = ((range[0] - safeMin) / (safeMax - safeMin)) * 100;
  const rangeEnd = ((range[1] - safeMin) / (safeMax - safeMin)) * 100;
  const rangeStyle: PriceRangeStyle = {
    "--price-range-start": `${rangeStart}%`,
    "--price-range-end": `${rangeEnd}%`,
  };

  return (
    <div className="bg-white shadow-1 rounded-lg">
      <div
        onClick={() => setToggleDropdown((current) => !current)}
        className="cursor-pointer flex items-center justify-between py-3 pl-6 pr-5.5"
      >
        <p className="text-dark">Precio</p>
        <button
          id="price-dropdown-btn"
          aria-label="button for price dropdown"
          className={`text-dark ease-out duration-200 ${toggleDropdown && "rotate-180"}`}
        >
          <svg className="fill-current" width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M4.43057 8.51192C4.70014 8.19743 5.17361 8.161 5.48811 8.43057L12 14.0122L18.5119 8.43057C18.8264 8.16101 19.2999 8.19743 19.5695 8.51192C19.839 8.82642 19.8026 9.29989 19.4881 9.56946L12.4881 15.5695C12.2072 15.8102 11.7928 15.8102 11.5119 15.5695L4.51192 9.56946C4.19743 9.29989 4.161 8.82641 4.43057 8.51192Z"
              fill=""
            />
          </svg>
        </button>
      </div>

      <div className={`p-6 ${toggleDropdown ? "block" : "hidden"}`}>
        <div className="price-range">
          <div className="price-range-slider" style={rangeStyle}>
            <div className="price-range-slider__track" aria-hidden="true" />
            <div className="price-range-slider__selected" aria-hidden="true" />
            <input
              className="price-range-slider__input price-range-slider__input--min"
              type="range"
              min={safeMin}
              max={safeMax}
              step={1}
              value={range[0]}
              aria-label="Precio mínimo"
              onChange={(event) => {
                const nextMin = Math.min(Number(event.target.value), range[1]);
                setRange([nextMin, range[1]]);
              }}
            />
            <input
              className="price-range-slider__input price-range-slider__input--max"
              type="range"
              min={safeMin}
              max={safeMax}
              step={1}
              value={range[1]}
              aria-label="Precio máximo"
              onChange={(event) => {
                const nextMax = Math.max(Number(event.target.value), range[0]);
                setRange([range[0], nextMax]);
              }}
            />
          </div>

          <div className="price-amount flex items-center justify-between pt-4">
            <div className="text-custom-xs text-dark-4 rounded border border-gray-3/80 px-3 py-1.5">
              {format(range[0])}
            </div>

            <div className="text-custom-xs text-dark-4 rounded border border-gray-3/80 px-3 py-1.5">
              {format(range[1])}
            </div>
          </div>

          <button
            type="button"
            onClick={() => onApply(range[0], range[1])}
            className="mt-4 inline-flex font-medium text-white bg-blue py-2 px-5 rounded-md ease-out duration-200 hover:bg-blue-dark"
          >
            {buttonLabels.applyPrice}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PriceDropdown;
