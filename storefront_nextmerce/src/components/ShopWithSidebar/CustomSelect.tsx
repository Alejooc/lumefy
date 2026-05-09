import React, { useEffect, useRef, useState } from "react";

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
  const [isOpen, setIsOpen] = useState(false);
  const selectRef = useRef<HTMLDivElement | null>(null);
  const selectedOption =
    options.find((option) => option.value === value) || options[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("click", handleClickOutside);
    return () => {
      document.removeEventListener("click", handleClickOutside);
    };
  }, []);

  return (
    <div className="custom-select custom-select-2 flex-shrink-0 relative" ref={selectRef}>
      <div
        className={`select-selected whitespace-nowrap ${isOpen ? "select-arrow-active" : ""}`}
        onClick={() => setIsOpen((current) => !current)}
      >
        {selectedOption?.label}
      </div>
      <div className={`select-items ${isOpen ? "" : "select-hide"}`}>
        {options.map((option) => (
          <div
            key={option.value}
            onClick={() => {
              onChange?.(option.value);
              setIsOpen(false);
            }}
            className={`select-item ${selectedOption?.value === option.value ? "same-as-selected" : ""}`}
          >
            {option.label}
          </div>
        ))}
      </div>
    </div>
  );
};

export default CustomSelect;
