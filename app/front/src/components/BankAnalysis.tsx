import { useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { calculateBankStats } from "@/lib/bankAnalytics";
import { formatCurrency, safeParseFloat } from "@/lib/formatters";
import { useOffers } from "@/hooks/useOffers";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from "recharts";
import { TrendingUp, DollarSign, FileText, Target, Loader2, PiggyBank } from "lucide-react";

export const BankAnalysis = () => {
  const { data: allOffers = [], isLoading } = useOffers();
  
  // Filtrar ofertas que têm dados básicos preenchidos
  const filteredOffers = allOffers.filter(offer => 
    offer.financed_amount && 
    offer.financed_amount !== 'null' && 
    offer.financed_amount !== null
  );
  
  // Convert Offer[] to BankOffer[] format
  const bankOffers = filteredOffers.map(offer => ({
    bank_name: offer.bank_name,
    year: offer.year,
    month: offer.month,
    monthly_interest_rate: offer.monthly_interest_rate,
    financed_amount: offer.financed_amount,
    asset_value: offer.asset_value,
    total_value_with_interest: offer.total_value_with_interest,
    installments_count: offer.installments_count,
    type: offer.type,
    offered: offer.offered,
  }));

  const bankStats = calculateBankStats(bankOffers);
  const [selectedBank, setSelectedBank] = useState<string>(bankStats[0]?.bank_name || "");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="flex items-center gap-3">
          <Loader2 className="animate-spin h-6 w-6 text-primary" />
          <span className="text-lg text-muted-foreground">Loading bank analysis...</span>
        </div>
      </div>
    );
  }

  if (bankStats.length === 0) {
    return (
      <div className="text-center p-12">
        <div className="text-muted-foreground text-lg">
          No data available for bank analysis
        </div>
      </div>
    );
  }

  const currentBankStats = bankStats.find((b) => b.bank_name === selectedBank);

  if (!currentBankStats) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Bank Analysis</h2>
          <p className="text-muted-foreground mt-1">
            Select a bank to view rate history and volume
          </p>
        </div>
        <Select value={selectedBank} onValueChange={setSelectedBank}>
          <SelectTrigger className="w-[300px]">
            <SelectValue placeholder="Select a bank" />
          </SelectTrigger>
          <SelectContent>
            {bankStats.map((bank) => (
              <SelectItem key={bank.bank_name} value={bank.bank_name}>
                {bank.bank_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card className="p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="bg-primary/10 rounded-xl p-3">
              <TrendingUp className="h-5 w-5 text-primary" />
            </div>
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Average Rate</p>
          <p className="text-2xl font-bold text-foreground">
            {(currentBankStats.avgRate * 100).toFixed(2)}%
          </p>
          <p className="text-xs text-muted-foreground mt-1">per month</p>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="bg-accent/10 rounded-xl p-3">
              <DollarSign className="h-5 w-5 text-accent" />
            </div>
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Total Volume</p>
          <p className="text-2xl font-bold text-foreground">
            {formatCurrency(currentBankStats.totalFinancing)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">in assets</p>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="bg-[#00D4AA]/10 rounded-xl p-3">
              <PiggyBank className="h-5 w-5" style={{ color: "#00D4AA" }} />
            </div>
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Interest Earned</p>
          <p className="text-2xl font-bold" style={{ color: "#00D4AA" }}>
            {formatCurrency(currentBankStats.totalInterestEarned)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">total interest</p>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="bg-secondary/10 rounded-xl p-3">
              <FileText className="h-5 w-5 text-secondary" />
            </div>
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Total Offers</p>
          <p className="text-2xl font-bold text-foreground">
            {currentBankStats.offerCount}
          </p>
          <p className="text-xs text-muted-foreground mt-1">identified</p>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="bg-accent/10 rounded-xl p-3">
              <Target className="h-5 w-5 text-accent" />
            </div>
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">BTG Covered</p>
          <p className="text-2xl font-bold text-accent">
            {currentBankStats.coveredCount}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            of {currentBankStats.offerCount} offers
          </p>
        </Card>
      </div>

      {/* System Type Distribution */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 text-foreground">System Distribution</h3>
        <div className="flex gap-4">
          <div className="flex-1 bg-primary/5 rounded-xl p-4 border border-primary/20">
            <p className="text-sm text-muted-foreground mb-2">PRICE (Automobiles)</p>
            <p className="text-3xl font-bold text-primary">{currentBankStats.priceCount}</p>
            <Badge variant="outline" className="mt-2">
              {((currentBankStats.priceCount / currentBankStats.offerCount) * 100).toFixed(0)}% of total
            </Badge>
          </div>
          <div className="flex-1 bg-secondary/5 rounded-xl p-4 border border-secondary/20">
            <p className="text-sm text-muted-foreground mb-2">SAC (Real Estate)</p>
            <p className="text-3xl font-bold text-secondary">{currentBankStats.sacCount}</p>
            <Badge variant="outline" className="mt-2">
              {((currentBankStats.sacCount / currentBankStats.offerCount) * 100).toFixed(0)}% of total
            </Badge>
          </div>
        </div>
      </Card>

      {/* Monthly Rate Chart */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 text-foreground">Interest Rate by Month</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={currentBankStats.monthlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis 
              dataKey="month" 
              stroke="hsl(var(--muted-foreground))"
              label={{ value: "Period", position: "insideBottom", offset: -5 }}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              label={{ value: "Rate (%)", angle: -90, position: "insideLeft" }}
              tickFormatter={(value) => `${(value * 100).toFixed(2)}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.5rem",
              }}
              formatter={(value: number) => `${(value * 100).toFixed(2)}%`}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="rate"
              stroke="hsl(var(--primary))"
              strokeWidth={3}
              name="Monthly Rate"
              dot={{ fill: "hsl(var(--primary))", r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* Monthly Volume Chart */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 text-foreground">Asset Value by Month</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={currentBankStats.monthlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis 
              dataKey="month" 
              stroke="hsl(var(--muted-foreground))"
              label={{ value: "Period", position: "insideBottom", offset: -5 }}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              label={{ value: "Volume (R$)", angle: -90, position: "insideLeft" }}
              tickFormatter={(value) =>
                new Intl.NumberFormat("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                }).format(value)
              }
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.5rem",
              }}
              formatter={(value: number) => formatCurrency(value)}
            />
            <Legend />
            <Bar
              dataKey="totalFinanced"
              fill="hsl(var(--accent))"
              name="Asset Value"
              radius={[8, 8, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* Monthly Interest Earned Chart */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 text-foreground">Interest Earned by Month</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={currentBankStats.monthlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis 
              dataKey="month" 
              stroke="hsl(var(--muted-foreground))"
              label={{ value: "Period", position: "insideBottom", offset: -5 }}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              label={{ value: "Interest (R$)", angle: -90, position: "insideLeft" }}
              tickFormatter={(value) =>
                new Intl.NumberFormat("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                }).format(value)
              }
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.5rem",
              }}
              formatter={(value: number) => formatCurrency(value)}
            />
            <Legend />
            <Bar
              dataKey="interestEarned"
              fill="#00D4AA"
              name="Interest Earned"
              radius={[8, 8, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
};
