export interface Offer {
  id: number;
  offer_id: string;
  bank_name: string;
  asset_value: string;
  financed_amount: string;
  installments_count: number;
  monthly_interest_rate: string;
  offered_interest_rate: string;
  savings_amount: string;
  total_value_with_interest: string;
  type: string;
  year: number;
  month: number;
  created_at: string;
  offered: boolean;
  user_id: number;
}

export interface ApiResponse {
  count: number;
  offers: Offer[];
  status: string;
}

const API_BASE_URL = "https://back.pedro-porto.com";

export const fetchOffers = async (): Promise<Offer[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/offers`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data: ApiResponse = await response.json();
    
    if (data.status !== "success") {
      throw new Error("API returned error status");
    }
    
    return data.offers;
  } catch (error) {
    console.error("Error fetching offers:", error);
    throw error;
  }
};
