import { safeParseFloat } from "./formatters";

export interface BankOffer {
  bank_name: string;
  year: number;
  month: number;
  monthly_interest_rate: string;
  financed_amount: string;
  asset_value: string;
  total_value_with_interest: string;
  installments_count: number;
  type: string;
  offered: boolean;
}

export interface BankStats {
  bank_name: string;
  avgRate: number;
  totalFinancing: number;
  totalInterestEarned: number;
  offerCount: number;
  priceCount: number;
  sacCount: number;
  coveredCount: number;
  monthlyData: {
    month: string;
    rate: number;
    totalFinanced: number;
    interestEarned: number;
    count: number;
  }[];
}

export const calculateBankStats = (offers: BankOffer[]): BankStats[] => {
  const bankMap = new Map<string, BankStats>();

  offers.forEach((offer) => {
    const bankName = offer.bank_name;
    const rate = safeParseFloat(offer.monthly_interest_rate);
    const financed = safeParseFloat(offer.financed_amount);
    const assetValue = safeParseFloat(offer.asset_value);
    const totalWithInterest = safeParseFloat(offer.total_value_with_interest);
    const interestEarned = totalWithInterest - financed; // Juros sobre o saldo devedor atual
    const monthKey = `${offer.month}/${offer.year}`;

    if (!bankMap.has(bankName)) {
      bankMap.set(bankName, {
        bank_name: bankName,
        avgRate: 0,
        totalFinancing: 0,
        totalInterestEarned: 0,
        offerCount: 0,
        priceCount: 0,
        sacCount: 0,
        coveredCount: 0,
        monthlyData: [],
      });
    }

    const stats = bankMap.get(bankName)!;
    stats.offerCount += 1;
    stats.totalFinancing += financed;
    stats.totalInterestEarned += interestEarned;
    
    if (offer.type === "automobile") {
      stats.priceCount += 1;
    } else if (offer.type === "property") {
      stats.sacCount += 1;
    }

    if (offer.offered) {
      stats.coveredCount += 1;
    }

    // Monthly data aggregation
    const existingMonth = stats.monthlyData.find((m) => m.month === monthKey);
    if (existingMonth) {
      existingMonth.totalFinanced += financed;
      existingMonth.interestEarned += interestEarned;
      existingMonth.count += 1;
      existingMonth.rate = (existingMonth.rate * (existingMonth.count - 1) + rate) / existingMonth.count;
    } else {
      stats.monthlyData.push({
        month: monthKey,
        rate,
        totalFinanced: financed,
        interestEarned: interestEarned,
        count: 1,
      });
    }
  });

  // Calculate average rates
  bankMap.forEach((stats) => {
    const totalRate = stats.monthlyData.reduce((sum, m) => sum + m.rate * m.count, 0);
    stats.avgRate = totalRate / stats.offerCount;
  });

  return Array.from(bankMap.values());
};

// Mock data for bank analytics
export const mockBankAnalytics: BankOffer[] = [
  {
    bank_name: "Banco Votorantim S/A",
    year: 2024,
    month: 8,
    monthly_interest_rate: "0.02630",
    financed_amount: "42500.00000",
    asset_value: "60000.00000",
    total_value_with_interest: "85000.00000",
    installments_count: 48,
    type: "automobile",
    offered: true,
  },
  {
    bank_name: "Banco Votorantim S/A",
    year: 2024,
    month: 7,
    monthly_interest_rate: "0.02580",
    financed_amount: "35000.00000",
    asset_value: "50000.00000",
    total_value_with_interest: "68000.00000",
    installments_count: 36,
    type: "automobile",
    offered: true,
  },
  {
    bank_name: "Banco Votorantim S/A",
    year: 2024,
    month: 9,
    monthly_interest_rate: "0.02690",
    financed_amount: "48000.00000",
    asset_value: "65000.00000",
    total_value_with_interest: "92000.00000",
    installments_count: 60,
    type: "property",
    offered: false,
  },
  {
    bank_name: "Banco Bradesco S/A",
    year: 2024,
    month: 8,
    monthly_interest_rate: "0.02890",
    financed_amount: "55000.00000",
    asset_value: "75000.00000",
    total_value_with_interest: "105000.00000",
    installments_count: 48,
    type: "automobile",
    offered: true,
  },
  {
    bank_name: "Banco Bradesco S/A",
    year: 2024,
    month: 7,
    monthly_interest_rate: "0.02850",
    financed_amount: "60000.00000",
    asset_value: "80000.00000",
    total_value_with_interest: "115000.00000",
    installments_count: 48,
    type: "automobile",
    offered: false,
  },
  {
    bank_name: "Banco Itaú Unibanco S/A",
    year: 2024,
    month: 8,
    monthly_interest_rate: "0.02720",
    financed_amount: "38000.00000",
    asset_value: "55000.00000",
    total_value_with_interest: "78000.00000",
    installments_count: 60,
    type: "property",
    offered: true,
  },
];
