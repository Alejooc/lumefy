export function formatMoney(
  value: number | null | undefined,
  _currency = "USD",
  showDecimals = false,
): string {
  const amount = Number.isFinite(value) ? Number(value) : 0;

  return new Intl.NumberFormat("es-CO", {
    style: "decimal",
    minimumFractionDigits: showDecimals ? 2 : 0,
    maximumFractionDigits: showDecimals ? 2 : 0,
  }).format(amount);
}
