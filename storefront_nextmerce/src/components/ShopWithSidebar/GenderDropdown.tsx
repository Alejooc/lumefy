"use client";

import React, { useState } from "react";

const GenderDropdown = ({
  types,
  onSelect,
}: {
  types: Array<{ name: string; value: string; products: number; isRefined: boolean }>;
  onSelect: (value?: string) => void;
}) => {
  const [toggleDropdown, setToggleDropdown] = useState(true);

  return (
    <div className="bg-white shadow-1 rounded-lg">
      <div
        onClick={() => setToggleDropdown((current) => !current)}
        className={`cursor-pointer flex items-center justify-between py-3 pl-6 pr-5.5 ${
          toggleDropdown && "shadow-filter"
        }`}
      >
        <p className="text-dark">Tipo de producto</p>
        <button
          aria-label="button for type dropdown"
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

      <div className={`flex-col gap-3 py-6 pl-6 pr-5.5 ${toggleDropdown ? "flex" : "hidden"}`}>
        <button
          type="button"
          className="group flex items-center justify-between ease-out duration-200 hover:text-blue"
          onClick={() => onSelect(undefined)}
        >
          <span>Todos los tipos</span>
        </button>
        {types.map((type) => (
          <button
            key={type.value}
            type="button"
            className={`${type.isRefined ? "text-blue" : ""} group flex items-center justify-between ease-out duration-200 hover:text-blue`}
            onClick={() => onSelect(type.value)}
          >
            <div className="flex items-center gap-2">
              <div
                className={`cursor-pointer flex items-center justify-center rounded w-4 h-4 border ${
                  type.isRefined ? "border-blue bg-blue" : "bg-white border-gray-3"
                }`}
              >
                <svg
                  className={type.isRefined ? "block" : "hidden"}
                  width="10"
                  height="10"
                  viewBox="0 0 10 10"
                  fill="none"
                >
                  <path
                    d="M8.33317 2.5L3.74984 7.08333L1.6665 5"
                    stroke="white"
                    strokeWidth="1.94437"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <span>{type.name}</span>
            </div>

            <span
              className={`${
                type.isRefined ? "text-white bg-blue" : "bg-gray-2"
              } inline-flex rounded-[30px] text-custom-xs px-2 ease-out duration-200 group-hover:text-white group-hover:bg-blue`}
            >
              {type.products}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default GenderDropdown;
