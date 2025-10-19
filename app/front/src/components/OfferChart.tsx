import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { TrendingDown } from "lucide-react";
import { formatCurrency, safeParseFloat } from "@/lib/formatters";
import { type Offer } from "@/lib/api";

interface OfferChartProps {
  offer: Offer;
}

export const OfferChart = ({ offer }: OfferChartProps) => {
  if (!offer.offered || !offer.offered_interest_rate) {
    return null;
  }

  const assetValue = safeParseFloat(offer.asset_value);
  const financedAmount = safeParseFloat(offer.financed_amount);
  const standardRate = safeParseFloat(offer.monthly_interest_rate);
  const offeredRate = safeParseFloat(offer.offered_interest_rate);
  const totalInstallments = offer.installments_count;
  
  // Calcular qual parcela atual baseado no saldo devedor
  // Assumindo PRICE: saldo = PV * (1+i)^k - PMT * ((1+i)^k - 1) / i
  // Resolver para k (parcelas já pagas)
  const calculateCurrentInstallment = () => {
    const i = standardRate;
    const pv = assetValue;
    const currentBalance = financedAmount;
    
    // PMT original
    const pmt = (pv * i * Math.pow(1 + i, totalInstallments)) / (Math.pow(1 + i, totalInstallments) - 1);
    
    // Aproximação: encontrar k onde o saldo é próximo ao atual
    for (let k = 0; k <= totalInstallments; k++) {
      const factor = Math.pow(1 + i, k);
      const balance = pv * factor - pmt * ((factor - 1) / i);
      
      if (balance <= currentBalance * 1.05 && balance >= currentBalance * 0.95) {
        return k;
      }
    }
    
    // Fallback: assumir que está na metade
    return Math.floor(totalInstallments * 0.4);
  };

  const currentInstallment = calculateCurrentInstallment();
  const remainingInstallments = totalInstallments - currentInstallment;

  // Calcular pagamentos mensais
  const calculateMonthlyPayment = (principal: number, rate: number, periods: number) => {
    if (rate === 0) return principal / periods;
    return (principal * rate * Math.pow(1 + rate, periods)) / (Math.pow(1 + rate, periods) - 1);
  };

  const currentPayment = calculateMonthlyPayment(assetValue, standardRate, totalInstallments);
  const btgPayment = calculateMonthlyPayment(financedAmount, offeredRate, remainingInstallments);

  // Gerar dados do gráfico - mostra histórico + futuro
  const chartData = [];
  
  // Histórico (parcelas já pagas com o banco atual)
  for (let i = 1; i <= currentInstallment; i++) {
    chartData.push({
      month: i,
      "Pagamento Atual": currentPayment,
      "Pagamento BTG": null, // Não havia BTG ainda
      phase: "Histórico"
    });
  }
  
  // Futuro (comparativo BTG vs continuar com atual)
  for (let i = currentInstallment + 1; i <= totalInstallments; i++) {
    chartData.push({
      month: i,
      "Pagamento Atual": currentPayment,
      "Pagamento BTG": btgPayment,
      phase: "Projeção"
    });
  }

  return (
    <div className="space-y-4">
      <div className="bg-gradient-to-r from-primary/5 to-accent/5 rounded-xl p-5 border border-primary/20">
        <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
          <TrendingDown className="h-5 w-5 text-primary" />
          Monthly Payment Comparison
        </h3>
        
        <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
          <div className="text-center">
            <p className="text-muted-foreground">Current Installment</p>
            <p className="text-lg font-bold text-foreground">
              {currentInstallment} of {totalInstallments}
            </p>
          </div>
          <div className="text-center">
            <p className="text-muted-foreground">Current Payment</p>
            <p className="text-lg font-bold text-red-600">
              {formatCurrency(currentPayment)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-muted-foreground">BTG Payment</p>
            <p className="text-lg font-bold text-green-600">
              {formatCurrency(btgPayment)}
            </p>
          </div>
        </div>
        
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis 
              dataKey="month" 
              stroke="hsl(var(--muted-foreground))"
              label={{ value: "Installment", position: "insideBottom", offset: -5 }}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              label={{ value: "Amount (R$)", angle: -90, position: "insideLeft" }}
              tickFormatter={(value) => formatCurrency(value)}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.5rem",
              }}
              formatter={(value: number | null) => 
                value ? formatCurrency(value) : "N/A"
              }
            />
            <Legend />
            
            {/* Linha vertical para marcar o ponto de transição */}
            <ReferenceLine 
              x={currentInstallment} 
              stroke="hsl(var(--primary))" 
              strokeDasharray="5 5"
              label={{ value: "BTG Start", position: "top" }}
            />
            
            <Line
              type="monotone"
              dataKey="Pagamento Atual"
              stroke="hsl(var(--destructive))"
              strokeWidth={3}
              name="Current Bank"
              dot={{ fill: "hsl(var(--destructive))", r: 3 }}
              connectNulls={true}
            />
            <Line
              type="monotone"
              dataKey="Pagamento BTG"
              stroke="#00D4AA"
              strokeWidth={3}
              name="BTG Pactual"
              dot={{ fill: "#00D4AA", r: 3 }}
              connectNulls={true}
            />
          </LineChart>
        </ResponsiveContainer>
        
        <div className="mt-4 text-sm text-muted-foreground">
          <p>
            <span className="inline-block w-3 h-3 bg-destructive rounded-full mr-2"></span>
            Red area: Installments already paid at current bank
          </p>
          <p>
            <span className="inline-block w-3 h-3 bg-green-600 rounded-full mr-2"></span>
            Green area: Potential savings with BTG from installment {currentInstallment + 1}
          </p>
        </div>
      </div>
    </div>
  );
};
