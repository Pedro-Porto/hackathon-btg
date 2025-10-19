import { useState } from "react";
import { DashboardHeader } from "@/components/DashboardHeader";
import { OffersTable } from "@/components/OffersTable";
import { OfferDetailsDialog } from "@/components/OfferDetailsDialog";
import { BankAnalysis } from "@/components/BankAnalysis";
import { type Offer } from "@/lib/api";
import { useOffers } from "@/hooks/useOffers";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TrendingDown, Building2, Target, BarChart3, Table, Loader2 } from "lucide-react";

const Index = () => {
  const [selectedOffer, setSelectedOffer] = useState<Offer | null>(null);
  const { data: allOffers = [], isLoading, error } = useOffers();

  // Filtrar ofertas que têm dados básicos preenchidos
  const offers = allOffers.filter(offer => 
    offer.financed_amount && 
    offer.financed_amount !== 'null' && 
    offer.financed_amount !== null
  );

  const totalOffers = offers.length;
  const offeredCount = offers.filter(o => o.offered).length;
  const totalSavings = offers.reduce((sum, o) => {
    const savings = parseFloat(o.savings_amount || "0");
    return sum + (isNaN(savings) ? 0 : savings);
  }, 0);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-subtle flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="animate-spin h-6 w-6 text-primary" />
          <span className="text-lg text-muted-foreground">Loading offers...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-subtle flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-lg font-medium mb-2">
            Error loading offers
          </div>
          <div className="text-muted-foreground">
            {error.message}
          </div>
        </div>
      </div>
    );
  }


  return (
    <div className="min-h-screen bg-gradient-subtle">
      <DashboardHeader />
      
      <main className="container mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">
            Market Credit Offers
          </h1>
          <p className="text-muted-foreground">
            Competitive rate analysis and BTG Pactual coverage opportunities
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-card rounded-2xl p-6 border border-border shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="bg-primary/10 rounded-xl p-3">
                <Building2 className="h-6 w-6 text-primary" />
              </div>
              <span className="text-3xl font-bold text-foreground">{totalOffers}</span>
            </div>
            <p className="text-sm font-medium text-muted-foreground">Identified Offers</p>
            <p className="text-xs text-muted-foreground mt-1">Last 30 days</p>
          </div>

          <div className="bg-card rounded-2xl p-6 border border-border shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="bg-accent/10 rounded-xl p-3">
                <Target className="h-6 w-6 text-accent" />
              </div>
              <span className="text-3xl font-bold text-accent">{offeredCount}</span>
            </div>
            <p className="text-sm font-medium text-muted-foreground">BTG Coverage</p>
            <p className="text-xs text-muted-foreground mt-1">Competitive rate offered</p>
          </div>

          <div className="bg-gradient-to-br from-accent/5 to-accent/10 rounded-2xl p-6 border border-accent/20 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="bg-accent/20 rounded-xl p-3">
                <TrendingDown className="h-6 w-6 text-accent" />
              </div>
              <span className="text-3xl font-bold text-accent">
                R$ {(totalSavings / 1000).toFixed(0)}k
              </span>
            </div>
            <p className="text-sm font-medium text-accent">Total Savings Generated</p>
            <p className="text-xs text-accent/70 mt-1">Accumulated competitive advantage</p>
          </div>
        </div>

        <Tabs defaultValue="offers" className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-2 mb-6">
            <TabsTrigger value="offers" className="flex items-center gap-2">
              <Table className="h-4 w-4" />
              Market Offers
            </TabsTrigger>
            <TabsTrigger value="analytics" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Bank Analysis
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="offers">
            <OffersTable 
              offers={offers} 
              onSelectOffer={setSelectedOffer}
            />
          </TabsContent>
          
          <TabsContent value="analytics">
            <BankAnalysis />
          </TabsContent>
        </Tabs>
      </main>

      <OfferDetailsDialog 
        offer={selectedOffer}
        onClose={() => setSelectedOffer(null)}
      />
    </div>
  );
};

export default Index;
