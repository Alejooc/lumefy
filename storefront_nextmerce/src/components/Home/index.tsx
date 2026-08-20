import React from "react";
import Hero from "./Hero";
import Categories from "./Categories";
import NewArrival from "./NewArrivals";
import PromoBanner from "./PromoBanner";
import BestSeller from "./BestSeller";
import CounDown from "./Countdown";
import Testimonials from "./Testimonials";
import ClosingCta from "./ClosingCta";

import { HomeViewModel } from "@/types/home";

const Home = ({ data }: { data: HomeViewModel }) => {
  return (
    <main>
      <Hero slides={data.heroSlides} promos={data.heroPromos} features={data.features} />
      <Categories items={data.categories} section={data.categorySection} />
      <NewArrival items={data.newArrivals} section={data.newArrivalsSection} />
      <PromoBanner items={data.promoBanners} />
      <BestSeller items={data.bestSellers} section={data.bestSellersSection} />
      <CounDown content={data.countdown} />
      <Testimonials section={data.testimonialsSection} items={data.testimonials} />
      <ClosingCta storeName={data.storeName} />
    </main>
  );
};

export default Home;
