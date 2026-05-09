import { Category } from "@/types/category";
import React from "react";
import Link from "next/link";

const SingleItem = ({ item }: { item: Category }) => {
  const overlayOpacity = typeof item.overlayOpacity === "number" ? Math.min(Math.max(item.overlayOpacity, 0), 1) : 0.18;

  return (
    <Link href={item.href || "#"} className="group flex flex-col items-center">
      <div
        className="max-w-[130px] w-full h-32.5 rounded-full overflow-hidden mb-4 relative"
        style={{ backgroundColor: item.backgroundColor || "#F2F3F8" }}
      >
        <div
          className="absolute inset-0 bg-center bg-cover transition-transform duration-500 group-hover:scale-105"
          style={{ backgroundImage: `url(${item.img})`, backgroundPosition: item.imagePosition || "center" }}
        />
        <div className="absolute inset-0" style={{ backgroundColor: `rgba(255,255,255,${overlayOpacity})` }} />
      </div>

      <div className="flex justify-center">
        <h3 className="inline-block font-medium text-center text-dark bg-gradient-to-r from-blue to-blue bg-[length:0px_1px] bg-left-bottom bg-no-repeat transition-[background-size] duration-500 hover:bg-[length:100%_3px] group-hover:bg-[length:100%_1px] group-hover:text-blue">
          {item.title}
        </h3>
      </div>
    </Link>
  );
};

export default SingleItem;
