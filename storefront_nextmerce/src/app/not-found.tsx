import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-gray-2 px-4 py-24">
      <div className="mx-auto max-w-[720px] rounded-xl bg-white px-8 py-16 text-center shadow-1">
        <p className="mb-3 text-sm font-medium uppercase tracking-[0.2em] text-blue">404</p>
        <h1 className="mb-4 text-3xl font-semibold text-dark">Página no encontrada</h1>
        <p className="mx-auto mb-8 max-w-[480px] text-dark-4">
          La página que buscas no existe o ya no está disponible en esta tienda.
        </p>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-md bg-blue px-6 py-3 font-medium text-white transition hover:bg-blue-dark"
        >
          Volver al inicio
        </Link>
      </div>
    </main>
  );
}
