export const DashboardHeader = () => {
  return (
    <header className="bg-gradient-to-r from-primary via-primary to-secondary shadow-lg">
      <div className="container mx-auto px-6">
        <div className="flex items-center justify-between h-20">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-lg font-bold text-white">BTG Pactual</h1>
              <p className="text-xs text-white/80">Competitive Intelligence • Credit Offer Analysis</p>
            </div>
          </div>
          
          <div className="hidden md:flex items-center gap-6 text-white/90 text-sm">
            <div className="text-right">
              <p className="font-medium">Internal Dashboard</p>
              <p className="text-xs text-white/70">Real-time monitoring</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
