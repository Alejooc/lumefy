import Image from "next/image";

import type { Testimonial } from "@/types/testimonial";

const SingleItem = ({ testimonial }: { testimonial: Testimonial }) => (
  <article className="min-h-[270px] rounded-[22px] border border-white/10 bg-white/[0.07] p-6 backdrop-blur-sm sm:p-7">
    <div className="mb-6 flex items-center gap-1 text-[#e6b18f]" aria-label="5 de 5 estrellas">
      {Array.from({ length: 5 }).map((_, index) => <span key={index} aria-hidden="true">★</span>)}
    </div>
    <blockquote className="text-base leading-7 text-white/90">“{testimonial.review}”</blockquote>
    <div className="mt-7 flex items-center gap-3.5">
      <div className="relative h-11 w-11 overflow-hidden rounded-full bg-white/10">
        <Image src={testimonial.authorImg} alt={testimonial.authorName} fill sizes="44px" className="object-cover" />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-white">{testimonial.authorName}</h3>
        <p className="mt-0.5 text-xs text-white/55">{testimonial.authorRole}</p>
      </div>
    </div>
  </article>
);

export default SingleItem;
