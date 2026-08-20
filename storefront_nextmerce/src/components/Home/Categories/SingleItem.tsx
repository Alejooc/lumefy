import Image from "next/image";
import Link from "next/link";

import type { Category } from "@/types/category";

const SingleItem = ({ item }: { item: Category }) => (
  <Link href={item.href || "/products"} className="group block">
    <div className="relative aspect-[4/5] overflow-hidden rounded-[20px] bg-[#eeeae4]">
      <Image
        src={item.img}
        alt={item.title}
        fill
        sizes="(max-width: 640px) 46vw, (max-width: 1024px) 30vw, 230px"
        className="object-cover transition duration-700 group-hover:scale-[1.045]"
        style={{ objectPosition: item.imagePosition || "center" }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-[#121827]/80 via-transparent to-transparent" />
      <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-2 p-4 text-white sm:p-5">
        <h3 className="text-sm font-semibold leading-tight sm:text-lg">{item.title}</h3>
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/40 bg-white/10 backdrop-blur-sm transition group-hover:bg-white group-hover:text-[#17233f]">
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
            <path d="M2.5 7.5h9M8 4l3.5 3.5L8 11" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </div>
    </div>
  </Link>
);

export default SingleItem;
