"use client";

import React, { useEffect, useState } from "react";

import SingleOrder from "./SingleOrder";
import { useStorefrontAuth } from "@/lib/storefront-auth";
import {
  getStorefrontAccountOrders,
  resolveStorefront,
  StorefrontApiError,
} from "@/lib/storefront-api";

type OrderRow = {
  orderId: string;
  createdAt: string;
  status: string;
  total: string;
  title: string;
};

const Orders = () => {
  const { session } = useStorefrontAuth();
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadOrders() {
      if (!session?.token) {
        if (active) {
          setOrders([]);
          setLoading(false);
        }
        return;
      }

      try {
        const storefront = await resolveStorefront();
        const rows = await getStorefrontAccountOrders(storefront.id, session.token);

        if (!active) {
          return;
        }

        setOrders(
          rows.map((order) => ({
            orderId: order.order_code,
            createdAt: new Date(order.created_at).toLocaleDateString("es-CO", {
              year: "numeric",
              month: "short",
              day: "numeric",
            }),
            status: order.status,
            total: new Intl.NumberFormat("es-CO", {
              style: "currency",
              currency: order.currency,
            }).format(order.total),
            title: order.title,
          })),
        );
      } catch (err) {
        if (!active) {
          return;
        }
        if (err instanceof StorefrontApiError) {
          setError(err.message);
        } else {
          setError("No pudimos cargar tus pedidos.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadOrders();

    return () => {
      active = false;
    };
  }, [session?.token]);

  if (loading) {
    return <p className="py-9.5 px-4 sm:px-7.5 xl:px-10">Cargando pedidos...</p>;
  }

  if (error) {
    return <p className="py-9.5 px-4 sm:px-7.5 xl:px-10 text-red">{error}</p>;
  }

  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-[770px]">
        {orders.length > 0 && (
          <div className="items-center justify-between py-4.5 px-7.5 hidden md:flex ">
            <div className="min-w-[111px]">
              <p className="text-custom-sm text-dark">Pedido</p>
            </div>
            <div className="min-w-[175px]">
              <p className="text-custom-sm text-dark">Fecha</p>
            </div>
            <div className="min-w-[128px]">
              <p className="text-custom-sm text-dark">Estado</p>
            </div>
            <div className="min-w-[213px]">
              <p className="text-custom-sm text-dark">Referencia</p>
            </div>
            <div className="min-w-[113px]">
              <p className="text-custom-sm text-dark">Total</p>
            </div>
            <div className="min-w-[113px]">
              <p className="text-custom-sm text-dark">Accion</p>
            </div>
          </div>
        )}
        {orders.length > 0 ? (
          orders.map((orderItem) => (
            <SingleOrder key={orderItem.orderId} orderItem={orderItem} smallView={false} />
          ))
        ) : (
          <p className="py-9.5 px-4 sm:px-7.5 xl:px-10">
            Aun no tienes pedidos registrados.
          </p>
        )}
      </div>

      {orders.map((orderItem) => (
        <SingleOrder key={`${orderItem.orderId}-mobile`} orderItem={orderItem} smallView={true} />
      ))}
    </div>
  );
};

export default Orders;
