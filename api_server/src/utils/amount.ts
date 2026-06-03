export function toActualAmount(amount: number): number {
  return Math.round(amount * 100);
}

export function fromActualAmount(amount: number): number {
  return amount / 100;
}
