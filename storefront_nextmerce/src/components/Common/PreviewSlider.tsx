"use client";

import { Swiper, SwiperSlide } from "swiper/react";
import { useCallback, useMemo, useRef } from "react";
import "swiper/css/navigation";
import "swiper/css";
import Image from "next/image";

import { usePreviewSlider } from "@/app/context/PreviewSliderContext";
import { useAppSelector } from "@/redux/store";

const FALLBACK_IMAGE = "/images/products/product-1-bg-1.png";

const PreviewSliderModal = () => {
  const { closePreviewModal, isModalPreviewOpen } = usePreviewSlider();
  const data = useAppSelector((state) => state.productDetailsReducer.value);
  const sliderRef = useRef(null);
  const images = useMemo(() => {
    const candidates = data?.imgs?.previews?.length
      ? data.imgs.previews
      : data?.imgs?.thumbnails?.length
        ? data.imgs.thumbnails
        : [FALLBACK_IMAGE];
    return Array.from(new Set(candidates.filter(Boolean)));
  }, [data]);

  const handlePrev = useCallback(() => {
    sliderRef.current?.swiper?.slidePrev();
  }, []);

  const handleNext = useCallback(() => {
    sliderRef.current?.swiper?.slideNext();
  }, []);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Galería de imágenes del producto"
      className={`preview-slider fixed inset-0 z-999999 flex h-screen w-full items-center justify-center bg-[#000000F2] px-4 sm:px-8 ${
        isModalPreviewOpen ? "" : "hidden"
      }`}
    >
      <button
        type="button"
        onClick={closePreviewModal}
        aria-label="Cerrar galería"
        className="absolute right-3 top-3 z-10 flex h-11 w-11 items-center justify-center rounded-full text-white transition hover:bg-white/10 hover:text-meta-5 sm:right-6 sm:top-6"
      >
        <svg className="fill-current" width="36" height="36" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path fillRule="evenodd" clipRule="evenodd" d="M14.3108 13L19.2291 8.08167C19.5866 7.72417 19.5866 7.12833 19.2291 6.77083C19.0543 6.59895 18.8189 6.50262 18.5737 6.50262C18.3285 6.50262 18.0932 6.59895 17.9183 6.77083L13 11.6892L8.08164 6.77083C7.90679 6.59895 7.67142 6.50262 7.42623 6.50262C7.18104 6.50262 6.94566 6.59895 6.77081 6.77083C6.41331 7.12833 6.41331 7.72417 6.77081 8.08167L11.6891 13L6.77081 17.9183C6.41331 18.2758 6.41331 18.8717 6.77081 19.2292C7.12831 19.5867 7.72414 19.5867 8.08164 19.2292L13 14.3108L17.9183 19.2292C18.2758 19.5867 18.8716 19.2291 19.2291C19.5866 18.8717 19.5866 18.2758 19.2291 17.9183L14.3108 13Z" />
        </svg>
      </button>

      <button
        type="button"
        aria-label="Imagen anterior"
        onClick={handlePrev}
        className="absolute left-1 z-10 rounded-full p-3 text-white transition hover:bg-white/10 sm:left-5 lg:left-12"
      >
        <svg className="rotate-180" width="36" height="36" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path fillRule="evenodd" clipRule="evenodd" d="M14.5918 5.92548C14.9091 5.60817 15.4236 5.60817 15.7409 5.92548L22.2409 12.4255C22.5582 12.7428 22.5582 13.2572 22.2409 13.5745L15.7409 20.0745C15.4236 20.3918 14.9091 20.3918 14.5918 20.0745C14.2745 19.7572 14.2745 19.2428 14.5918 18.9255L19.7048 13.8125H4.33301C3.88428 13.8125 3.52051 13.4487 3.52051 13C3.52051 12.5513 3.88428 12.1875 4.33301 12.1875H19.7048L14.5918 7.07452C14.2745 6.75722 14.2745 6.24278 14.5918 5.92548Z" fill="currentColor" />
        </svg>
      </button>

      <button
        type="button"
        aria-label="Imagen siguiente"
        onClick={handleNext}
        className="absolute right-1 z-10 rounded-full p-3 text-white transition hover:bg-white/10 sm:right-5 lg:right-12"
      >
        <svg width="36" height="36" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path fillRule="evenodd" clipRule="evenodd" d="M14.5918 5.92548C14.9091 5.60817 15.4236 5.60817 15.7409 5.92548L22.2409 12.4255C22.5582 12.7428 22.5582 13.2572 22.2409 13.5745L15.7409 20.0745C15.4236 20.3918 14.9091 20.3918 14.5918 20.0745C14.2745 19.7572 14.2745 19.2428 14.5918 18.9255L19.7048 13.8125H4.33301C3.88428 13.8125 3.52051 13.4487 3.52051 13C3.52051 12.5513 3.88428 12.1875 4.33301 12.1875H19.7048L14.5918 7.07452C14.2745 6.75722 14.2745 6.24278 14.5918 5.92548Z" fill="currentColor" />
        </svg>
      </button>

      <Swiper ref={sliderRef} slidesPerView={1} spaceBetween={20} className="h-[78vh] w-[min(88vw,900px)]">
        {images.map((image, index) => (
          <SwiperSlide key={`${image}-${index}`} className="!flex items-center justify-center">
            <div className="relative h-full w-full">
              <Image
                src={image}
                alt={`${data?.title || "Producto"} — imagen ${index + 1}`}
                fill
                priority={index === 0}
                sizes="90vw"
                className="object-contain"
              />
            </div>
          </SwiperSlide>
        ))}
      </Swiper>
    </div>
  );
};

export default PreviewSliderModal;
