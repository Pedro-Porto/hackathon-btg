import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { OfferChart } from "./OfferChart";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, safeCurrency, safePercentage } from "@/lib/formatters";
import { type Offer } from "@/lib/api";
import { Calendar, TrendingDown, DollarSign, Percent, Building2, CheckCircle2 } from "lucide-react";

interface OfferDetailsDialogProps {
  offer: Offer | null;
  onClose: () => void;
}

export const OfferDetailsDialog = ({ offer, onClose }: OfferDetailsDialogProps) => {
  if (!offer) return null;

  return (
    <Dialog open={!!offer} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl flex items-center gap-3">
            <Building2 className="h-6 w-6 text-primary" />
            <span className="text-primary">Detailed Competitive Analysis</span>
            <Badge variant="outline" className="ml-2 font-mono">
              #{offer.offer_id}
            </Badge>
          </DialogTitle>
          <DialogDescription className="text-base">
            {offer.bank_name} • {offer.type === "automobile" ? "Auto Financing" : "Real Estate Financing"}
          </DialogDescription>
        </DialogHeader>

        {/* Status Banner */}
        {offer.offered && (
          <div className="bg-accent/10 border border-accent/30 rounded-xl p-4 flex items-center gap-3">
            <div className="bg-accent/20 rounded-full p-2">
              <CheckCircle2 className="h-5 w-5 text-accent" />
            </div>
            <div>
              <p className="font-semibold text-accent">Opportunity Covered by BTG</p>
              <p className="text-sm text-accent/80">
                Competitive offer was presented with more attractive rate
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 my-6">
          <div className="bg-muted/30 rounded-xl p-4 border border-border">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <DollarSign className="h-4 w-4" />
              <span className="text-sm font-medium">Asset Value</span>
            </div>
            <p className="text-xl font-bold text-foreground">
              {safeCurrency(offer.asset_value)}
            </p>
          </div>

          <div className="bg-muted/30 rounded-xl p-4 border border-border">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <DollarSign className="h-4 w-4" />
              <span className="text-sm font-medium">Outstanding Balance</span>
            </div>
            <p className="text-xl font-bold text-foreground">
              {safeCurrency(offer.financed_amount)}
            </p>
          </div>

          <div className="bg-primary/5 rounded-xl p-4 border border-primary/20">
            <div className="flex items-center gap-2 text-primary mb-2">
              <Percent className="h-4 w-4" />
              <span className="text-sm font-medium">Competitor Rate</span>
            </div>
            <p className="text-xl font-bold text-primary">
              {safePercentage(offer.monthly_interest_rate)}
            </p>
          </div>

          <div className="bg-accent/10 rounded-xl p-4 border border-accent/30">
            <div className="flex items-center gap-2 text-accent mb-2">
              <TrendingDown className="h-4 w-4" />
              <span className="text-sm font-medium">BTG Savings</span>
            </div>
            <p className="text-xl font-bold text-accent">
              {safeCurrency(offer.savings_amount)}
            </p>
          </div>
        </div>

        {/* Comparison Box */}
        <div className="bg-gradient-to-r from-primary/5 to-accent/5 rounded-xl p-5 border border-primary/20 mb-6">
          <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
            <Percent className="h-5 w-5 text-primary" />
            Rate Comparison
          </h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-muted-foreground mb-1">{offer.bank_name} Rate</p>
              <p className="text-2xl font-bold text-foreground">
                {safePercentage(offer.monthly_interest_rate)} p.m.
              </p>
            </div>
            <div>
              <p className="text-sm text-accent mb-1">BTG Pactual Offered Rate</p>
              <p className="text-2xl font-bold text-accent">
                {offer.offered ? `${safePercentage(offer.offered_interest_rate)} p.m.` : "Under analysis"}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-muted/20 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2 text-muted-foreground mb-3">
            <Calendar className="h-4 w-4" />
            <span className="text-sm font-semibold">Financing Details</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Installments:</span>{" "}
              <span className="font-semibold text-foreground">{offer.installments_count}x</span>
            </div>
            <div>
              <span className="text-muted-foreground">Total with Interest:</span>{" "}
              <span className="font-semibold text-foreground">
                {safeCurrency(offer.total_value_with_interest)}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Period:</span>{" "}
              <span className="font-semibold text-foreground">
                {offer.month}/{offer.year}
              </span>
            </div>
          </div>
        </div>

        <OfferChart offer={offer} />
      </DialogContent>
    </Dialog>
  );
};
