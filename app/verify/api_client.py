import logging
from typing import Dict, Optional
import requests

logger = logging.getLogger(__name__)


class APIClient:
    
    def __init__(self, post_url: str):
        self.post_url = post_url
    
    def send_recommendation(
        self, 
        trigger: bool, 
        source_id: Optional[int] = None, 
        agent_analysis: Optional[Dict] = None
    ):
        try:
            if trigger and source_id and agent_analysis:
                payload = {
                    'source_id': source_id,
                    'agent_analysis': agent_analysis,
                    'trigger_recommendation': True
                }
            else:
                payload = {
                    'trigger_recommendation': False
                }
            
            response = requests.post(self.post_url, json=payload, timeout=5)
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Error sending recommendation: {e}", exc_info=True)

