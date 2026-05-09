"use client";
import React, { useState } from "react";

function toSwatchColor(value: string): string {
  const normalized = value.trim().toLowerCase();
  const palette: Record<string, string> = {
    black: "#111827",
    negro: "#111827",
    white: "#f9fafb",
    blanco: "#f9fafb",
    blue: "#2563eb",
    azul: "#2563eb",
    red: "#dc2626",
    rojo: "#dc2626",
    green: "#16a34a",
    verde: "#16a34a",
    yellow: "#eab308",
    amarillo: "#eab308",
    pink: "#ec4899",
    rosado: "#ec4899",
    rosa: "#ec4899",
    purple: "#9333ea",
    morado: "#9333ea",
    orange: "#f97316",
    naranja: "#f97316",
    gray: "#6b7280",
    grey: "#6b7280",
    gris: "#6b7280",
    brown: "#92400e",
    cafe: "#92400e",
    marron: "#92400e",
    beige: "#d6d3d1",
  };
  return palette[normalized] || "#9ca3af";
}

const ColorsDropdwon = ({
  colors,
  activeColor,
  onSelect,
}: {
  colors: { value: string; products: number; isRefined: boolean }[];
  activeColor?: string[];
  onSelect: (value?: string) => void;
}) => {
  const [toggleDropdown, setToggleDropdown] = useState(true);

  return (
    <div className="bg-white shadow-1 rounded-lg">
      <div
        onClick={() => setToggleDropdown(!toggleDropdown)}
        className={`cursor-pointer flex items-center justify-between py-3 pl-6 pr-5.5 ${
          toggleDropdown && "shadow-filter"
        }`}
      >
        <p className="text-dark">Colores</p>
        <button
          aria-label="button for colors dropdown"
          className={`text-dark ease-out duration-200 ${
            toggleDropdown && "rotate-180"
          }`}
        >
          <svg
            className="fill-current"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M4.43057 8.51192C4.70014 8.19743 5.17361 8.161 5.48811 8.43057L12 14.0122L18.5119 8.43057C18.8264 8.16101 19.2999 8.19743 19.5695 8.51192C19.839 8.82642 19.8026 9.29989 19.4881 9.56946L12.4881 15.5695C12.2072 15.8102 11.7928 15.8102 11.5119 15.5695L4.51192 9.56946C4.19743 9.29989 4.161 8.82641 4.43057 8.51192Z"
              fill=""
            />
          </svg>
        </button>
      </div>

      {/* <!-- dropdown menu --> */}
      <div
        className={`flex-wrap gap-2.5 p-6 ${
          toggleDropdown ? "flex" : "hidden"
        }`}
      >
        <button
          type="button"
          onClick={() => onSelect(undefined)}
          className={`cursor-pointer select-none flex items-center rounded-md border px-3 py-1 text-sm ${
            !activeColor?.length ? "border-blue text-blue" : "border-transparent"
          }`}
        >
          Todos
        </button>
        {colors.map((color, key) => (
          <label
            key={key}
            htmlFor={color.value}
            className="cursor-pointer select-none flex items-center"
          >
            <div className="relative">
              <input
                type="radio"
                name="color"
                id={color.value}
                className="sr-only"
                checked={color.isRefined}
                onChange={() => onSelect(color.value)}
              />
                <div
                  className={`flex items-center justify-center w-5.5 h-5.5 rounded-full ${
                  color.isRefined && "border"
                }`}
                style={{ borderColor: toSwatchColor(color.value) }}
              >
                <span
                  className="block w-3 h-3 rounded-full"
                  style={{ backgroundColor: toSwatchColor(color.value) }}
                ></span>
              </div>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
};

export default ColorsDropdwon;
