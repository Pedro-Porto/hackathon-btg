import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, safeCurrency, safePercentage } from "@/lib/formatters";
import { type Offer } from "@/lib/api";
import { TrendingDown, CheckCircle2, XCircle } from "lucide-react";

interface OffersTableProps {
  offers: Offer[];
  onSelectOffer: (offer: Offer) => void;
}

export const OffersTable = ({ offers, onSelectOffer }: OffersTableProps) => {
  return (
    <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30 border-b border-border">
              <TableHead className="font-semibold text-foreground">ID</TableHead>
              <TableHead className="font-semibold text-foreground">Competitor Bank</TableHead>
              <TableHead className="font-semibold text-foreground">Asset Value</TableHead>
              <TableHead className="font-semibold text-foreground">Outstanding Balance</TableHead>
              <TableHead className="font-semibold text-foreground">Installments</TableHead>
              <TableHead className="font-semibold text-foreground">Bank Rate</TableHead>
              <TableHead className="font-semibold text-foreground">Our Offer</TableHead>
              <TableHead className="font-semibold text-foreground">BTG Savings</TableHead>
              <TableHead className="font-semibold text-foreground">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {offers.map((offer) => (
              <TableRow
                key={offer.id}
                className="cursor-pointer hover:bg-primary/5 transition-colors border-b border-border/50"
                onClick={() => onSelectOffer(offer)}
              >
                <TableCell className="font-mono font-medium text-primary">
                  #{offer.offer_id}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-primary"></div>
                    <span className="font-medium">{offer.bank_name}</span>
                  </div>
                </TableCell>
                <TableCell className="font-semibold">
                  {safeCurrency(offer.asset_value)}
                </TableCell>
                <TableCell>
                  {safeCurrency(offer.financed_amount)}
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="font-medium">
                    {offer.installments_count}x
                  </Badge>
                </TableCell>
                <TableCell>
                  <span className="text-muted-foreground font-medium">
                    {safePercentage(offer.monthly_interest_rate)}
                  </span>
                </TableCell>
                <TableCell>
                  {offer.offered ? (
                    <span className="text-primary font-bold">
                      {safePercentage(offer.offered_interest_rate)}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </TableCell>
                <TableCell>
                  {offer.offered ? (
                    <div className="flex items-center gap-1.5 text-accent font-bold">
                      <TrendingDown className="h-4 w-4" />
                      {safeCurrency(offer.savings_amount)}
                    </div>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </TableCell>
                <TableCell>
                  {offer.offered ? (
                    <Badge className="bg-accent hover:bg-accent/90 text-white border-0">
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      Covered
                    </Badge>
                  ) : (
                    <Badge variant="destructive" className="border-0">
                      <XCircle className="h-3 w-3 mr-1" />
                      Not Covered
                    </Badge>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};
