export function formatMoney(
  value: number | null | undefined,
  currency = "USD",
  showDecimals = false,
): string {
  const amount = Number.isFinite(value) ? Number(value) : 0;
  const currencyCode = /^[A-Z]{3}$/i.test(currency) ? currency.toUpperCase() : "USD";

  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: currencyCode,
    currencyDisplay: "narrowSymbol",
    minimumFractionDigits: showDecimals ? 2 : 0,
    maximumFractionDigits: showDecimals ? 2 : 0,
  })
    .format(amount)
    .replace(/\s+/g, "");
}
