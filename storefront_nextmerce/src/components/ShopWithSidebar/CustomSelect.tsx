import React, { useId } from "react";

type Option = {
  label: string;
  value: string;
};

const CustomSelect = ({
  options,
  value,
  onChange,
}: {
  options: Option[];
  value?: string;
  onChange?: (value: string) => void;
}) => {
  const selectId = useId();

  return (
    <div className="relative flex-shrink-0">
      <label htmlFor={selectId} className="sr-only">Ordenar productos</label>
      <select
        id={selectId}
        value={value || options[0]?.value}
        onChange={(event) => onChange?.(event.target.value)}
        className="min-h-9 cursor-pointer rounded-md border border-gray-3 bg-white py-1.5 pl-3 pr-9 text-sm font-medium text-dark outline-none transition focus:border-blue focus:ring-2 focus:ring-blue/20"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </div>
  );
};

export default CustomSelect;
