export function formatMoney(
  value: number | null | undefined,
  currency = "USD",
  showDecimals = false,
): string {
  const amount = Number.isFinite(value) ? Number(value) : 0;

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    currencyDisplay: "code",
    minimumFractionDigits: showDecimals ? 2 : 0,
    maximumFractionDigits: showDecimals ? 2 : 0,
  }).format(amount);
}
