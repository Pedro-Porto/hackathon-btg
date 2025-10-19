import logging
import time
import json
import uuid
from typing import Dict, Any, Optional
from interest_calculator import InterestCalculator
from database_matcher import DatabaseMatcher
from llm import LLMWrapper

logger = logging.getLogger(__name__)


class MessageMatcher:
    
    def __init__(self, database_matcher: DatabaseMatcher, kafka_publisher, llm: LLMWrapper):
        self.calculator = InterestCalculator()
        self.database = database_matcher
        self.kafka_publisher = kafka_publisher
        self.llm = llm
    
    def validate_schema(self, message_value: Dict[str, Any]) -> bool:
        if not isinstance(message_value, dict):
            logger.warning(f"Message discarded: expected dict but got {type(message_value).__name__}")
            return False
        
        if not isinstance(message_value.get('source_id'), int):
            logger.warning(f"Message discarded: missing or invalid 'source_id'")
            return False
        
        agent_analysis = message_value.get('agent_analysis')
        if not isinstance(agent_analysis, dict):
            logger.warning(f"Message discarded: missing or invalid 'agent_analysis'")
            return False
        
        if not isinstance(agent_analysis.get('installment_count'), int):
            logger.warning(f"Message discarded: missing or invalid 'installment_count'")
            return False
        
        if not isinstance(agent_analysis.get('current_installment_number'), int):
            logger.warning(f"Message discarded: missing or invalid 'current_installment_number'")
            return False
        
        if not isinstance(agent_analysis.get('installment_amount'), (int, float)):
            logger.warning(f"Message discarded: missing or invalid 'installment_amount'")
            return False
        
        financing_info = message_value.get('financing_info')
        if not isinstance(financing_info, dict):
            logger.warning(f"Message discarded: missing or invalid 'financing_info'")
            return False
        
        if not isinstance(financing_info.get('type'), str):
            logger.warning(f"Message discarded: missing or invalid 'financing_info.type'")
            return False
        
        if not isinstance(financing_info.get('value'), (int, float)):
            logger.warning(f"Message discarded: missing or invalid 'financing_info.value'")
            return False
        
        return True
    
    def calculate_remaining_amount(
        self,
        total_value: float,
        installment_count: int,
        current_installment_number: int,
        system_type: str,
        monthly_rate: float,
        installment_amount: float
    ) -> float:
        remaining_installments = installment_count - current_installment_number + 1
        
        if system_type == 'SAC':
            # SAC: amortização constante
            amortization = total_value / installment_count
            remaining_amount = amortization * remaining_installments
        else:  # PRICE system
            # Saldo = PMT × [1 - (1+i)^(-n)] / i
            r = monthly_rate / 100  # Convert percentage to decimal
            if r == 0:  # Avoid division by zero
                remaining_amount = installment_amount * remaining_installments
            else:
                remaining_amount = installment_amount * (1 - (1 + r)**(-remaining_installments)) / r
        
        return remaining_amount
    
    def calculate_potential_savings(
        self,
        remaining_amount: float,
        remaining_installments: int,
        current_rate: float,
        new_rate: float
    ) -> float:
        current_total_interest = remaining_amount * (current_rate / 100) * remaining_installments
        new_total_interest = remaining_amount * (new_rate / 100) * remaining_installments
        
        savings = current_total_interest - new_total_interest
        return max(0, savings)
    
    def process(self, message_value: Dict[str, Any]):
        try:
            if not self.validate_schema(message_value):
                return
            
            source_id = message_value['source_id']
            agent_analysis = message_value['agent_analysis']
            financing_info = message_value['financing_info']
            timestamp = message_value.get('timestamp', int(time.time()))
            
            financing_type = financing_info['type'].lower()
            total_value = float(financing_info['value'])
            installment_count = agent_analysis['installment_count']
            current_installment_number = agent_analysis['current_installment_number']
            installment_amount = float(agent_analysis['installment_amount'])
            company = agent_analysis.get('company', 'Unknown')
            
            interest_rate = None
            system_type = None
            
            if financing_type == 'automobile':
                system_type = 'PRICE'
                interest_rate = self.calculator.calculate_price_interest_rate(
                    total_value=total_value,
                    installment_count=installment_count,
                    installment_amount=installment_amount
                )
            elif financing_type == 'property':
                system_type = 'SAC'
                interest_rate = self.calculator.calculate_sac_interest_rate(
                    total_value=total_value,
                    installment_count=installment_count,
                    current_installment_number=current_installment_number,
                    installment_amount=installment_amount
                )
            else:
                logger.warning(f"Unknown financing type: {financing_type}")
                return
            
            if interest_rate is None:
                logger.warning(f"Could not calculate interest rate for source_id={source_id}")
                return
            
            print("\n" + "="*80)
            print(f"INTEREST RATE CALCULATION - Source ID: {source_id}")
            print("="*80)
            print(f"Company: {company}")
            print(f"Financing Type: {financing_type.upper()}")
            print(f"Amortization System: {system_type}")
            print(f"Total Value: R$ {total_value:,.2f}")
            print(f"Installment Amount: R$ {installment_amount:,.2f}")
            print(f"Total Installments: {installment_count}")
            print(f"Current Installment: {current_installment_number}")
            print(f"\n>>> MONTHLY INTEREST RATE: {interest_rate:.4f}% <<<")
            print(f">>> ANNUAL INTEREST RATE: {interest_rate * 12:.4f}% <<<")
            
            logger.info(f"Interest rate calculated: {interest_rate:.4f}% per month for source_id={source_id}")
            
            remaining_amount = self.calculate_remaining_amount(
                total_value=total_value,
                installment_count=installment_count,
                current_installment_number=current_installment_number,
                system_type=system_type,
                monthly_rate=interest_rate,
                installment_amount=installment_amount
            )
            
            remaining_installments = installment_count - current_installment_number + 1
            
            print(f"Remaining Amount: R$ {remaining_amount:,.2f}")
            print(f"Remaining Installments: {remaining_installments}")
            print(f"Current Monthly Rate Being Paid: {interest_rate:.4f}%")
            print("="*80 + "\n")
            
            best_offer = self.database.find_best_offer(
                financing_type=system_type,
                current_rate=interest_rate,
                remaining_amount=remaining_amount
            )
            
            if best_offer:
                new_rate_percent = best_offer['tax_mes'] * 100
                
                potential_savings = self.calculate_potential_savings(
                    remaining_amount=remaining_amount,
                    remaining_installments=remaining_installments,
                    current_rate=interest_rate,
                    new_rate=new_rate_percent
                )
                
                matched_message = {
                    "source_id": source_id,
                    "agent_analysis": agent_analysis,
                    "eligible_offer": {
                        "remaining_finance_amount": round(remaining_amount, 2),
                        "current_finance_month_tax": round(interest_rate, 2),
                        "new_finance_month_tax": round(new_rate_percent, 2),
                        "new_financing_amount": round(best_offer['max_amount'], 2),
                        "potential_savings": round(potential_savings, 2)
                    },
                    "offer_available": True,
                    "timestamp": timestamp
                }
                
                print("="*80)
                print("BETTER OFFER FOUND!")
                print("="*80)
                print(f"Offer Name: {best_offer['name']}")
                print(f"Current Rate: {interest_rate:.4f}%")
                print(f"New Rate: {new_rate_percent:.4f}%")
                print(f"Potential Savings: R$ {potential_savings:,.2f}")
                print("="*80 + "\n")
                
                logger.info(f"Better offer found for source_id={source_id}, publishing to btg.matched")
            else:
                matched_message = {
                    "source_id": source_id,
                    "agent_analysis": agent_analysis,
                    "offer_available": False,
                    "timestamp": timestamp
                }
                
                print("="*80)
                print("NO BETTER OFFER AVAILABLE")
                print("="*80 + "\n")
                
                logger.info(f"No better offer found for source_id={source_id}")
            
            self.kafka_publisher.send('btg.matched', matched_message)
            logger.info(f"Message published to btg.matched for source_id={source_id}")
            
            self.update_financing_offer(
                message_value=message_value,
                financing_type=financing_type,
                total_value=total_value,
                interest_rate=interest_rate,
                installment_count=installment_count,
                has_offer=best_offer is not None,
                best_offer=best_offer,
                remaining_amount=remaining_amount,
                potential_savings=potential_savings if best_offer else 0
            )
                
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
    
    def check_bank_with_llm(self, company_name: str, banks: list) -> Optional[int]:
        try:
            bank_list = "\n".join([f"- {b['name']} (ID: {b['id']})" for b in banks])
            
            system_prompt = (
                "You are a banking system assistant. Your job is to match company names to existing banks. "
                "Return ONLY a valid JSON object with the bank ID. No markdown, no explanations."
            )
            
            prompt = f"""Company name from analysis: "{company_name}"

Available banks in our database:
{bank_list}

Which bank ID matches this company? Return ONLY JSON format:
{{"id": 123}}"""
            
            response = self.llm.generate(prompt=prompt, system_prompt=system_prompt)
            
            logger.info(f"LLM response for bank matching: {response}")
            
            response_clean = response.strip()
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                response_clean = "\n".join([l for l in lines if not l.startswith("```")])
            
            result = json.loads(response_clean)
            return result.get('id')
            
        except Exception as e:
            logger.error(f"Error checking bank with LLM: {e}", exc_info=True)
            return None
    
    def update_financing_offer(
        self,
        message_value: Dict[str, Any],
        financing_type: str,
        total_value: float,
        interest_rate: float,
        installment_count: int,
        has_offer: bool,
        best_offer: Optional[Dict],
        remaining_amount: float,
        potential_savings: float
    ):
        try:
            agent_analysis = message_value.get('agent_analysis', {})
            user_data = message_value.get('user_data', {})
            financing_info = message_value.get('financing_info', {})
            
            company_name = agent_analysis.get('company', '')
            if not company_name:
                logger.warning("No company name found in agent_analysis")
                return
            
            user_metadata = user_data.get('user_metadata', {})
            user_id = user_metadata.get('id')
            if not user_id:
                logger.warning("No user_id found in user_data")
                return
            
            banks = self.database.get_all_banks()
            if not banks:
                logger.warning("No banks in database")
                return
            
            bank_id = self.check_bank_with_llm(company_name, banks)
            if not bank_id:
                logger.warning(f"Could not match company '{company_name}' to any bank")
                return
            
            total_with_interest = total_value * (1 + (interest_rate / 100) * installment_count)
            
            if has_offer and best_offer:
                new_rate_percent = best_offer['tax_mes'] * 100
                financing_type_id = str(best_offer['id'])
                
                self.database.update_bank_financing_offer(
                    bank_id=bank_id,
                    user_id=user_id,
                    asset_value=total_value,
                    monthly_interest_rate=interest_rate / 100,
                    total_value_with_interest=total_with_interest,
                    installments_count=installment_count,
                    financing_type=financing_type,
                    offered=True,
                    offered_interest_rate=new_rate_percent / 100,
                    offer_id=financing_type_id,
                    financed_amount=remaining_amount,
                    savings_amount=potential_savings
                )
                logger.info(f"Financing offer updated with offer for bank_id={bank_id}, user_id={user_id}")
            else:
                self.database.update_bank_financing_offer(
                    bank_id=bank_id,
                    user_id=user_id,
                    asset_value=total_value,
                    monthly_interest_rate=interest_rate / 100,
                    total_value_with_interest=total_with_interest,
                    installments_count=installment_count,
                    financing_type=financing_type,
                    offered=False
                )
                logger.info(f"Financing offer updated without offer for bank_id={bank_id}, user_id={user_id}")
                
        except Exception as e:
            logger.error(f"Error updating financing offer: {e}", exc_info=True)
