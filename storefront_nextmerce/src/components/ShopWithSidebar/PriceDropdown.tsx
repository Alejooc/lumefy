import { useEffect, useState } from "react";
import RangeSlider from "react-range-slider-input";
import "react-range-slider-input/dist/style.css";
import { useStorefrontCurrency } from "@/lib/storefront-currency";

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
  const [range, setRange] = useState<[number, number]>([selectedMin, selectedMax || max]);
  const { currency } = useStorefrontCurrency();

  useEffect(() => {
    setRange([selectedMin, selectedMax || max]);
  }, [max, selectedMax, selectedMin]);

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
          <RangeSlider
            id="range-slider-gradient"
            className="margin-lg"
            min={min}
            max={Math.max(max, min + 1)}
            value={range}
            step={1}
            onInput={(values) => setRange([Math.floor(values[0]), Math.ceil(values[1])])}
          />

          <div className="price-amount flex items-center justify-between pt-4">
            <div className="text-custom-xs text-dark-4 flex rounded border border-gray-3/80">
              <span className="block border-r border-gray-3/80 px-2.5 py-1.5">{currency}</span>
              <span className="block px-3 py-1.5">{range[0]}</span>
            </div>

            <div className="text-custom-xs text-dark-4 flex rounded border border-gray-3/80">
              <span className="block border-r border-gray-3/80 px-2.5 py-1.5">{currency}</span>
              <span className="block px-3 py-1.5">{range[1]}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => onApply(range[0], range[1])}
            className="mt-4 inline-flex font-medium text-white bg-blue py-2 px-5 rounded-md ease-out duration-200 hover:bg-blue-dark"
          >
            Aplicar precio
          </button>
        </div>
      </div>
    </div>
  );
};

export default PriceDropdown;
