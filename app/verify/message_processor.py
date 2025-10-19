import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from typing import Dict, Any
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import DatabaseManager
from api_client import APIClient
from core.llm import LLMWrapper


class MessageProcessor:
    
    def __init__(self, database_manager: DatabaseManager, api_client: APIClient, llm: LLMWrapper):
        self.database = database_manager
        self.api_client = api_client
        self.llm = llm
    
    def validate_schema(self, message_value: Dict[str, Any]) -> bool:
        if not isinstance(message_value.get('source_id'), int):
            print(f"Message discarded: missing or invalid 'source_id' (expected int). Message: {message_value}")
            return False
        
        if not isinstance(message_value.get('timestamp'), int):
            print(f"Message discarded: missing or invalid 'timestamp' (expected int). Message: {message_value}")
            return False
        
        agent_analysis = message_value.get('agent_analysis')
        if not isinstance(agent_analysis, dict):
            print(f"Message discarded: missing or invalid 'agent_analysis' (expected dict). Message: {message_value}")
            return False
        
        if not isinstance(agent_analysis.get('company'), str):
            print(f"Message discarded: missing or invalid 'agent_analysis.company' (expected string). Message: {message_value}")
            return False
        
        if not isinstance(agent_analysis.get('installment_count'), int):
            print(f"Message discarded: missing or invalid 'agent_analysis.installment_count' (expected int). Message: {message_value}")
            return False
        
        if not isinstance(agent_analysis.get('current_installment_number'), int):
            print(f"Message discarded: missing or invalid 'agent_analysis.current_installment_number' (expected int). Message: {message_value}")
            return False
        
        installment_amount = agent_analysis.get('installment_amount')
        if not isinstance(installment_amount, (int, float)):
            print(f"Message discarded: missing or invalid 'agent_analysis.installment_amount' (expected float/int). Message: {message_value}")
            return False
        
        return True
    
    def process(self, message_value: Dict[str, Any]):
        try:
            if not self.validate_schema(message_value):
                return
            
            source_id = message_value['source_id']
            agent_analysis = message_value['agent_analysis']
            installment_amount = agent_analysis['installment_amount']
            
            if installment_amount <= 300:
                print(f"Installment amount {installment_amount} is below minimum threshold (300), skipping source_id={source_id}")
                self.api_client.send_recommendation(False, None, None)
                return
            
            user_id = self.database.get_user_id_from_source(source_id)
            
            if user_id is None:
                print(f"user_id not found for source_id={source_id}")
                self.api_client.send_recommendation(False, None, None)
                return
            
            has_matching_transaction = self.database.check_matching_transaction(user_id, installment_amount)
            
            if has_matching_transaction:
                self.api_client.send_recommendation(True, source_id, agent_analysis)
                print(f"Recommendation sent for source_id={source_id}, user_id={user_id}")
                
                self.process_bank_and_offer(agent_analysis, user_id)
            else:
                self.api_client.send_recommendation(False, None, None)
                print(f"No matching transaction for source_id={source_id}, user_id={user_id}")
                
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def process_bank_and_offer(self, agent_analysis: Dict[str, Any], user_id: int):
        try:
            company_name = agent_analysis.get('company', '')
            if not company_name:
                print("No company name found in agent_analysis")
                return
            
            banks = self.database.get_all_banks()
            
            if not banks:
                print(f"No banks in database, adding {company_name} as new bank")
                bank_id = None
            else:
                bank_id = self.check_bank_with_llm(company_name, banks)
            
            if bank_id is None:
                bank_id = self.database.add_bank(company_name)
                if bank_id is None:
                    print(f"Failed to add bank: {company_name}")
                    return
            
            installments_count = agent_analysis.get('installment_count', 0)
            current_installment = agent_analysis.get('current_installment_number', 0)
            
            now = datetime.now()
            start_date = now - relativedelta(months=current_installment - 1)
            
            self.database.insert_bank_financing_offer(
                bank_id=bank_id,
                user_id=user_id,
                month=start_date.month,
                year=start_date.year,
                installments_count=installments_count
            )
            
        except Exception as e:
            print(f"Error processing bank and offer: {e}")
    
    def check_bank_with_llm(self, company_name: str, banks: list) -> int:
        try:
            bank_list = "\n".join([f"- {b['name']} (ID: {b['id']})" for b in banks])
            
            system_prompt = (
                "You are a banking system assistant. Your job is to match company names to existing banks. "
                "Return ONLY a valid JSON object, nothing else. No markdown, no explanations."
            )
            
            prompt = f"""Company name from analysis: "{company_name}"

Available banks in our database:
{bank_list}

Is this company name one of the banks above? If yes, return the ID. If no, it's a new bank.

Return ONLY this JSON format:
{{"new_name": false, "id": 123}}  (if it matches)
OR
{{"new_name": true}}  (if it's a new bank)"""
            
            response = self.llm.generate(prompt=prompt, system_prompt=system_prompt)
            
            print(f"LLM response for bank matching: {response}")
            
            response_clean = response.strip()
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                response_clean = "\n".join([l for l in lines if not l.startswith("```")])
            
            result = json.loads(response_clean)
            
            if not result.get('new_name', True):
                return result.get('id')
            return None
            
        except Exception as e:
            print(f"Error checking bank with LLM: {e}")
            return None

