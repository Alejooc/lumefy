import OrderDetails from "./OrderDetails";

const OrderModal = ({ showDetails, toggleModal, order }: any) => {
  if (!showDetails) {
    return null;
  }

  return (
    <>
      <div
        className={`backdrop-filter-sm visible fixed left-0 top-0 z-[99999] flex min-h-screen w-full justify-center items-center bg-[#000]/40 px-4 py-8 sm:px-8`}
      >
        <div className="shadow-7 relative w-full max-w-[600px] max-h-[calc(100vh-4rem)] overflow-y-auto scale-100 transform rounded-[15px] bg-white transition-all">
          <button
            onClick={() => toggleModal(false)}
            type="button"
            aria-label="Cerrar detalle del pedido"
            className="text-body absolute right-3 top-3 z-[9999] flex h-10 w-10 items-center justify-center rounded-full border border-gray-3 bg-white hover:text-dark"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 25 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M12.9983 10.586L17.9483 5.63603L19.3623 7.05003L14.4123 12L19.3623 16.95L17.9483 18.364L12.9983 13.414L8.04828 18.364L6.63428 16.95L11.5843 12L6.63428 7.05003L8.04828 5.63603L12.9983 10.586Z"
                fill="currentColor"
              ></path>
            </svg>
          </button>

          <OrderDetails orderItem={order} />
        </div>
      </div>
    </>
  );
};

export default OrderModal;
