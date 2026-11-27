/**
 * Comparator dùng chung cho các cột bảng có thể sắp xếp.
 * So sánh số, ngày, boolean và chuỗi theo kiểu tự nhiên (NV2 đứng trước NV10).
 */
export type TableSortSelector<T> = string | ((record: T) => unknown);

function compareValues(left: unknown, right: unknown): number {
  const leftEmpty = left === null || left === undefined || left === "";
  const rightEmpty = right === null || right === undefined || right === "";
  if (leftEmpty || rightEmpty) {
    if (leftEmpty && rightEmpty) return 0;
    return leftEmpty ? -1 : 1;
  }

  if (typeof left === "boolean" && typeof right === "boolean") {
    return Number(left) - Number(right);
  }

  if (typeof left === "number" && typeof right === "number") {
    return left - right;
  }

  const leftText = String(left).trim();
  const rightText = String(right).trim();
  const numericPattern = /^-?\d+(?:\.\d+)?$/;
  if (numericPattern.test(leftText) && numericPattern.test(rightText)) {
    return Number(leftText) - Number(rightText);
  }

  const datePattern = /^\d{4}-\d{2}-\d{2}(?:[T\s].*)?$/;
  if (datePattern.test(leftText) && datePattern.test(rightText)) {
    const leftTime = Date.parse(leftText);
    const rightTime = Date.parse(rightText);
    if (Number.isFinite(leftTime) && Number.isFinite(rightTime)) {
      return leftTime - rightTime;
    }
  }

  return leftText.localeCompare(rightText, "vi", {
    numeric: true,
    sensitivity: "base",
  });
}

export function tableSorter<T extends object>(selector: TableSortSelector<T>) {
  const read = typeof selector === "function"
    ? selector
    : (record: T) => (record as Record<string, unknown>)[selector];

  return (left: T, right: T): number => compareValues(read(left), read(right));
}
