import { useQuery } from "@tanstack/react-query";
import { fetchOffers, type Offer } from "@/lib/api";

export const useOffers = () => {
  return useQuery<Offer[], Error>({
    queryKey: ["offers"],
    queryFn: fetchOffers,
    refetchInterval: 30000, // Refetch every 30 seconds
    staleTime: 10000, // Consider data stale after 10 seconds
  });
};
