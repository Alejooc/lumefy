import React from "react";

function statusLabel(status: string): string {
  return {
    processing: "En preparación",
    delivered: "Entregado",
    "on-hold": "En espera",
    cancelled: "Cancelado",
  }[status] || status;
}

const OrderDetails = ({ orderItem }: { orderItem: {
  orderId: string;
  createdAt: string;
  status: string;
  total: string;
  title: string;
  shippingAddress?: string;
} }) => {
  return (
    <div className="p-5 sm:p-7.5">
      <h3 className="mb-5 text-xl font-medium text-dark">Detalle del pedido</h3>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-dark-4">Pedido</p>
          <p className="mt-1 font-medium text-dark">#{orderItem.orderId.slice(-8)}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-dark-4">Fecha</p>
          <p className="mt-1 text-dark">{orderItem.createdAt}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-dark-4">Estado</p>
          <p className="mt-1 text-dark">{statusLabel(orderItem.status)}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-dark-4">Total</p>
          <p className="mt-1 font-medium text-dark">{orderItem.total}</p>
        </div>
      </div>
      <div className="mt-5 border-t border-gray-3 pt-5">
        <p className="text-xs uppercase tracking-wide text-dark-4">Producto principal</p>
        <p className="mt-1 text-dark">{orderItem.title}</p>
      </div>
      {orderItem.shippingAddress ? (
        <div className="mt-5 border-t border-gray-3 pt-5">
          <p className="text-xs uppercase tracking-wide text-dark-4">Dirección de entrega</p>
          <p className="mt-1 text-dark">{orderItem.shippingAddress}</p>
        </div>
      ) : null}
    </div>
  );
};

export default OrderDetails;
