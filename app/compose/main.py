import os
import sys
import time
from typing import Any, Dict, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.llm import LLMWrapper
from core.kafka import KafkaJSON


KAFKA_BOOTSTRAP = os.getenv("KAFKA_BROKER_URL", "localhost:29092")
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "btg.matched")
OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC", "btg.composed")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.pedro-porto.com")



def ts_ms() -> int:
    return int(time.time() * 1000)

def fmt_brl(v: Optional[float]) -> str:
    if v is None:
        return "-"
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def fmt_pct(v: Optional[float]) -> str:
    if v is None:
        return "-"
    s = f"{v:.2f}".replace(".", ",")
    return f"{s}% a.m."


SYSTEM = (
    "Você é um copywriter bancário do banco BTG pactual. Escreva mensagens curtas, claras, amigáveis e profissionais, "
    "em português do Brasil. Evite jargões, use frases curtas. Não inclua markdown, emojis ou listas. "
    "Você está ajudando clientes a refinanciar ou portar financiamentos vindos de outras instituições. "
    "Responda sempre apenas com o texto final."
)

NO_OFFER_TPL = """Dados do cliente:
- Banco/empresa externa: {company}
- Parcela atual: {current_installment_number} de {installment_count}
- Valor da parcela: {installment_amount}

Escreva uma mensagem curta avisando que, por enquanto, não há oferta de refinanciamento/portabilidade disponível.
Mostre-se à disposição para avisar quando surgir oportunidade. Máx. 450 caracteres."""

YES_OFFER_TPL = """Dados do cliente:
- Banco/empresa externa: {company}
- Parcela atual: {current_installment_number} de {installment_count}
- Valor da parcela: {installment_amount}

Oferta detectada:
- Saldo a financiar (atual): {remaining_finance_amount}
- Taxa mensal atual: {current_finance_month_tax}
- Nova taxa mensal: {new_finance_month_tax}
- Novo valor financiado: {new_financing_amount}
- Economia potencial estimada: {potential_savings}

Escreva uma mensagem curta convidando o cliente a avançar com a proposta.
Mencione com naturalidade a nova taxa e a economia potencial (sem exagero), e ofereça ajuda para simular/contratar.
Máx. 550 caracteres."""

def compose_with_llm(llm: LLMWrapper, payload: Dict[str, Any]) -> str:
    aa = payload.get("agent_analysis", {}) or {}
    company = aa.get("company")
    cur = aa.get("current_installment_number")
    tot = aa.get("installment_count")
    amt = aa.get("installment_amount")

    has_offer = bool(payload.get("offer_available")) and bool(payload.get("eligible_offer"))
    if has_offer:
        eo = payload.get("eligible_offer", {}) or {}
        prompt = YES_OFFER_TPL.format(
            company=company or "-",
            current_installment_number=cur if cur is not None else "-",
            installment_count=tot if tot is not None else "-",
            installment_amount=fmt_brl(amt),
            remaining_finance_amount=fmt_brl(eo.get("remaining_finance_amount")),
            current_finance_month_tax=fmt_pct(eo.get("current_finance_month_tax")),
            new_finance_month_tax=fmt_pct(eo.get("new_finance_month_tax")),
            new_financing_amount=fmt_brl(eo.get("new_financing_amount")),
            potential_savings=fmt_brl(eo.get("potential_savings")),
        )
    else:
        prompt = NO_OFFER_TPL.format(
            company=company or "-",
            current_installment_number=cur if cur is not None else "-",
            installment_count=tot if tot is not None else "-",
            installment_amount=fmt_brl(amt),
        )

    text = llm.generate(prompt=prompt, system_prompt=SYSTEM).strip()
    return text


def fallback_message(payload: Dict[str, Any]) -> str:
    aa = payload.get("agent_analysis", {}) or {}
    company = aa.get("company") or "seu banco"
    cur = aa.get("current_installment_number")
    tot = aa.get("installment_count")
    amt = aa.get("installment_amount")

    base_info = []
    if cur is not None and tot is not None:
        base_info.append(f"parcela {cur} de {tot}")
    if amt is not None:
        base_info.append(f"valor de {fmt_brl(amt)}")

    info = f" ({', '.join(base_info)})" if base_info else ""
    if payload.get("offer_available") and payload.get("eligible_offer"):
        eo = payload.get("eligible_offer", {}) or {}
        taxa_nova = eo.get("new_finance_month_tax")
        eco = eo.get("potential_savings")
        p1 = f"Identificamos uma condição melhor para seu financiamento no {company}{info}."
        p2 = f"Nova taxa a.m.: {fmt_pct(taxa_nova)}. Economia estimada: {fmt_brl(eco)}."
        p3 = "Podemos avançar com a simulação e contratação agora mesmo. Posso te ajudar?"
        return " ".join([p1, p2, p3])
    else:
        return (f"Analisamos seu financiamento no {company}{info} e, por enquanto, "
                "não há uma oferta melhor disponível. Fico de olho e te aviso assim que surgir uma oportunidade. "
                "Se quiser, posso revisar seus dados ou refazer a simulação.")


def build_output(source_id: int, offer_message: str) -> Dict[str, Any]:
    return {
        "source_id": int(source_id),
        "offer_message": offer_message,
        "timestamp": ts_ms(),
    }

def on_msg(topic: str, msg: Dict[str, Any], *, k: KafkaJSON, llm: LLMWrapper):
    try:
        source_id = int(msg.get("source_id", 0))
    except Exception:
        source_id = 0

    try:
        text = compose_with_llm(llm, msg)
        if not text or text == "{}":
            raise ValueError("LLM empty")
    except Exception:
        text = fallback_message(msg)

    out = build_output(source_id, text)

    if hasattr(k, "send"):
        k.send(OUTPUT_TOPIC, out)
    elif hasattr(k, "publish"):
        k.publish(OUTPUT_TOPIC, out)
    else:
        raise AttributeError("KafkaJSON não possui 'send' nem 'publish'.")

    print("[COMPOSED]", out)


def main():
    llm = LLMWrapper(
        provider=LLM_PROVIDER,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        ollama_base_url=OLLAMA_BASE_URL,
    )
    k = KafkaJSON(KAFKA_BOOTSTRAP, os.getenv("GROUP_ID", "btg-composer"))
    k.subscribe(INPUT_TOPIC)
    k.loop(lambda t, d: on_msg(t, d, k=k, llm=llm))


if __name__ == "__main__":
    main()
