from typing import Dict, Any, Optional
from database_enricher import DatabaseEnricher


class MessageEnricher:
    
    def __init__(self, database_enricher: DatabaseEnricher):
        self.database = database_enricher
    
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
        
        financing_info = message_value.get('financing_info')
        if not isinstance(financing_info, dict):
            print(f"Message discarded: missing or invalid 'financing_info' (expected dict). Message: {message_value}")
            return False
        
        if not isinstance(financing_info.get('type'), str):
            print(f"Message discarded: missing or invalid 'financing_info.type' (expected string). Message: {message_value}")
            return False
        
        if not isinstance(financing_info.get('value'), (int, float)):
            print(f"Message discarded: missing or invalid 'financing_info.value' (expected float/int). Message: {message_value}")
            return False
        
        return True
    
    def enrich(self, message_value: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if not isinstance(message_value, dict):
                print(f"Message discarded: expected dict but got {type(message_value).__name__}. Message: {message_value}")
                return None
            
            if not self.validate_schema(message_value):
                return None
            
            source_id = message_value['source_id']
            
            user_id = self.database.get_user_id_from_source(source_id)
            
            if user_id is None:
                print(f"user_id not found for source_id={source_id}, cannot enrich message")
                return None
            
            user_metadata = self.database.get_user_metadata(user_id)
            if user_metadata is None:
                print(f"user_metadata not found for user_id={user_id}")
                return None
            
            account_data = self.database.get_account_data(user_id)
            if account_data is None:
                print(f"account data not found for user_id={user_id}, using defaults")
                account_data = {
                    "balance": 0.0,
                    "credit_limit": 0.0,
                    "credit_usage": 0.0
                }
            
            transactions = self.database.get_transactions(user_id)
            investments = self.database.get_investments(user_id)
            
            enriched_message = {
                "source_id": source_id,
                "agent_analysis": message_value['agent_analysis'],
                "user_data": {
                    "user_metadata": user_metadata,
                    "account": account_data,
                    "transactions": transactions,
                    "investments": investments
                },
                "financing_info": message_value['financing_info'],
                "timestamp": message_value['timestamp']
            }
            
            print(f"Message enriched successfully for source_id={source_id}, user_id={user_id}")
            return enriched_message
                
        except Exception as e:
            print(f"Error enriching message: {e}")
            return None

