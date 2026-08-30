import { useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";

const ITEMS_PER_COLUMN = 6;

const Dropdown = ({ menuItem, stickyMenu }) => {
  const [dropdownToggler, setDropdownToggler] = useState(false);
  const pathUrl = usePathname();
  const columns = [];

  for (let index = 0; index < menuItem.submenu.length; index += ITEMS_PER_COLUMN) {
    columns.push(menuItem.submenu.slice(index, index + ITEMS_PER_COLUMN));
  }

  return (
    <li
      className="group"
    >
      <button
        type="button"
        onClick={() => setDropdownToggler(!dropdownToggler)}
        aria-expanded={dropdownToggler}
        className={`relative hover:text-blue text-custom-sm font-medium text-dark flex items-center gap-1.5 capitalize before:w-0 before:h-[3px] before:bg-blue before:absolute before:left-0 before:bottom-0 before:rounded-t-[3px] before:ease-out before:duration-200 hover:before:w-full ${
          stickyMenu ? "xl:py-4" : "xl:py-6"
        } ${menuItem.path && pathUrl === menuItem.path && "!text-blue before:!w-full"}`}
      >
        {menuItem.title}
        <svg
          className="fill-current cursor-pointer"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M2.95363 5.67461C3.13334 5.46495 3.44899 5.44067 3.65866 5.62038L7.99993 9.34147L12.3412 5.62038C12.5509 5.44067 12.8665 5.46495 13.0462 5.67461C13.2259 5.88428 13.2017 6.19993 12.992 6.37964L8.32532 10.3796C8.13808 10.5401 7.86178 10.5401 7.67453 10.3796L3.00787 6.37964C2.7982 6.19993 2.77392 5.88428 2.95363 5.67461Z"
            fill=""
          />
        </svg>
      </button>

      {/* <!-- Dropdown Start --> */}
      <ul
        className={`dropdown ${dropdownToggler ? "flex" : ""} xl:flex-row xl:group-hover:translate-y-0`}
      >
        {columns.map((column, columnIndex) => (
          <li className="xl:min-w-[220px] xl:flex-[0_1_220px]" key={columnIndex}>
            <ul className="flex flex-col gap-1">
              {column.map((item) => (
                <li key={item.id}>
                  <Link
                    href={item.path}
                    className={`flex min-h-[2.75rem] items-center rounded-[0.35rem] text-custom-sm hover:text-blue hover:bg-gray-1 py-[7px] px-4.5 ${
                      pathUrl === item.path && "text-blue bg-gray-1"
                    } `}
                  >
                    {item.title}
                  </Link>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </li>
  );
};

export default Dropdown;
