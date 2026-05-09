import React, { useState, useEffect } from "react";

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
  const [selectedOption, setSelectedOption] = useState<Option>(options[0]);

  useEffect(() => {
    const nextSelected =
      options.find((option) => option.value === value) || options[0];
    setSelectedOption(nextSelected);
  }, [options, value]);

  const toggleDropdown = () => {
    setIsOpen(!isOpen);
  };

  const handleOptionClick = (option: Option) => {
    setSelectedOption(option);
    setIsOpen(false);
    onChange?.(option.value);
  };

  useEffect(() => {
    // closing modal while clicking outside
    function handleClickOutside(event) {
      if (isOpen && !event.target.closest(".dropdown-content")) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div className="dropdown-content custom-select relative" style={{ width: "200px" }}>
      <div
        className={`select-selected whitespace-nowrap ${
          isOpen ? "select-arrow-active" : ""
        }`}
        onClick={toggleDropdown}
      >
        {selectedOption.label}
      </div>
      <div className={`select-items ${isOpen ? "" : "select-hide"}`}>
        {options.map((option, index) => (
          <div
            key={index}
            onClick={() => handleOptionClick(option)}
            className={`select-item ${
              selectedOption === option ? "same-as-selected" : ""
            }`}
          >
            {option.label}
          </div>
        ))}
      </div>
    </div>
  );
};

export default CustomSelect;
