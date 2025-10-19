import math
from typing import Optional


class InterestCalculator:
    
    @staticmethod
    def calculate_sac_interest_rate(
        total_value: float,
        installment_count: int,
        current_installment_number: int,
        installment_amount: float
    ) -> Optional[float]:
        try:
            amortization = total_value / installment_count
            
            remaining_installments = installment_count - current_installment_number + 1
            current_balance = amortization * remaining_installments
            
            interest_amount = installment_amount - amortization
            
            if current_balance <= 0:
                print("Current balance is zero or negative, cannot calculate interest rate")
                return None
            
            monthly_interest_rate = interest_amount / current_balance
            
            return monthly_interest_rate * 100
            
        except Exception as e:
            print(f"Error calculating SAC interest rate: {e}", exc_info=True)
            return None
    
    @staticmethod
    def calculate_price_interest_rate(
        total_value: float,
        installment_count: int,
        installment_amount: float,
        tolerance: float = 1e-6,
        max_iterations: int = 100
    ) -> Optional[float]:
        try:
            if installment_amount <= 0 or total_value <= 0 or installment_count <= 0:
                print("Invalid input values for PRICE calculation")
                return None
            
            lower_bound = 0.0
            upper_bound = 1.0
            
            for _ in range(max_iterations):
                mid = (lower_bound + upper_bound) / 2
                
                if mid == 0:
                    calculated_pmt = total_value / installment_count
                else:
                    calculated_pmt = total_value * (mid * math.pow(1 + mid, installment_count)) / (math.pow(1 + mid, installment_count) - 1)
                
                if abs(calculated_pmt - installment_amount) < tolerance:
                    return mid * 100
                
                if calculated_pmt < installment_amount:
                    lower_bound = mid
                else:
                    upper_bound = mid
            
            final_rate = (lower_bound + upper_bound) / 2
            return final_rate * 100
            
        except Exception as e:
            print(f"Error calculating PRICE interest rate: {e}", exc_info=True)
            return None

