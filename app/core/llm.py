import requests
import json
import re
from typing import Optional, Dict, Any, List


class LLMWrapper:
    """
    Wrapper simples para chamadas a modelos LLM (Ollama local ou OpenAI API).
    """

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen2.5:7b-instruct",
        temperature: float = 0.0,
        ollama_base_url: str = "https://ollama.pedro-porto.com",
        openai_api_key: Optional[str] = None,
        openai_model: Optional[str] = None,
        timeout_s: int = 60,
    ):
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model or model
        self.timeout_s = timeout_s

    # ----------------------------------------------------
    # API pública
    # ----------------------------------------------------
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Gera texto a partir de um prompt.
        """
        if self.provider == "ollama":
            return self._generate_ollama(prompt, system_prompt)
        elif self.provider == "openai":
            return self._generate_openai(prompt, system_prompt)
        else:
            raise ValueError(f"Provedor '{self.provider}' não suportado.")

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Interface estilo Chat — recebe lista de mensagens [{"role": "user"/"system"/"assistant", "content": "..."}]
        """
        if self.provider == "ollama":
            return self._chat_ollama(messages)
        elif self.provider == "openai":
            return self._chat_openai(messages)
        else:
            raise ValueError(f"Provedor '{self.provider}' não suportado.")

    # ----------------------------------------------------
    # Implementações específicas
    # ----------------------------------------------------
    def _generate_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Chamada ao Ollama via /api/generate.
        """
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt or ''}\n{prompt}",
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        r = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json=payload,
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()

    def _chat_ollama(self, messages: List[Dict[str, str]]) -> str:
        """
        Chamada ao Ollama via /api/chat.
        """
        payload = {"model": self.model, "messages": messages, "stream": False}
        r = requests.post(
            f"{self.ollama_base_url}/api/chat",
            json=payload,
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "").strip()

    def _generate_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Chamada à OpenAI Chat Completions API.
        """
        import openai  # precisa de pip install openai

        openai.api_key = self.openai_api_key
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = openai.ChatCompletion.create(
            model=self.openai_model,
            messages=messages,
            temperature=self.temperature,
        )
        return resp["choices"][0]["message"]["content"].strip()

    def _chat_openai(self, messages: List[Dict[str, str]]) -> str:
        import openai
        openai.api_key = self.openai_api_key
        resp = openai.ChatCompletion.create(
            model=self.openai_model,
            messages=messages,
            temperature=self.temperature,
        )
        return resp["choices"][0]["message"]["content"].strip()

    # ----------------------------------------------------
    # Utilidades opcionais
    # ----------------------------------------------------
    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Tenta extrair o primeiro JSON válido de uma resposta de modelo.
        """
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
if __name__ == "__main__":
    llm = LLMWrapper(provider="ollama", model="qwen2.5:7b-instruct")
    resposta = llm.generate("Resuma o texto: A inteligência artificial está transformando o mundo.")
    print(resposta)