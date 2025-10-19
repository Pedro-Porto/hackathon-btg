export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
};

export const safeParseFloat = (value: string | null | undefined): number => {
  if (!value || value === 'null' || value === 'undefined') {
    return 0;
  }
  const parsed = parseFloat(value);
  return isNaN(parsed) ? 0 : parsed;
};

export const safeCurrency = (value: string | null | undefined): string => {
  const parsed = safeParseFloat(value);
  if (parsed === 0) return "N/A";
  return formatCurrency(parsed);
};

export const safePercentage = (value: string | null | undefined, decimals: number = 2): string => {
  const parsed = safeParseFloat(value);
  if (parsed === 0) return "N/A";
  return `${(parsed * 100).toFixed(decimals)}%`;
};

export const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(2)}%`;
};

export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};
