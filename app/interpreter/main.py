import sys
import os
import json
import re
from typing import Any, Dict, Optional, List, Callable, Tuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.llm import LLMWrapper
from core.kafka import KafkaJSON


INPUT_TOPIC = os.getenv("INPUT_TOPIC", "btg.parsed")
OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC", "btg.interpreted")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
GROUP_ID = os.getenv("GROUP_ID", "btg-interpreter-simple")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.pedro-porto.com")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")  # ajuste p/ qwen2.5:7b-instruct após pull
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
DEBUG = os.getenv("DEBUG", "0") == "1"

def extract_brl_amount(text: str) -> Optional[float]:
    """
    Extrai um valor monetário de um texto:
      - prioriza PT-BR: 1.234,56 / 630,62
      - fallback US: 1234.56
    """
    if not text:
        return None
    t = " ".join(str(text).split())

    # 1) formato brasileiro
    m = re.search(r"(?<!\d)(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})(?!\d)", t)
    if m:
        v = m.group(1).replace(".", "").replace(",", ".")
        try:
            return float(v)
        except ValueError:
            pass

    # 2) formato com ponto decimal
    m = re.search(r"(?<!\d)(\d+\.\d{2})(?!\d)", t)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    return None


def find_amount(att: List[Dict[str, Any]]) -> Optional[float]:
    """
    Heurística para valor da parcela:
      1) prioriza labels fortes (score) + maior 'value_conf'
      2) fallback: maior confiança com qualquer padrão monetário
    """
    def score_label(label: str) -> int:
        L = (label or "").upper().replace("\n", " ")
        score = 0
        # fortes / comuns em OCR
        if "VALOR DO DOCUMENTO" in L or "DOCUMENTO VALOR DO" in L or "VALOR DO" in L:
            score += 4
        if "VALOR PARCELA" in L or "VALOR DA PARCELA" in L:
            score += 3
        if "VALOR" in L:
            score += 2
        if "DOCUMENTO" in L:
            score += 1
        return score

    candidates = []
    for it in att:
        label = it.get("label_text") or ""
        value = it.get("value_text") or ""
        conf = float(it.get("value_conf", 0.0))
        s = score_label(label)
        if s > 0:
            amt = extract_brl_amount(value)
            if amt is not None:
                candidates.append((s, conf, amt, label, value))

    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best = candidates[0]
        if DEBUG:
            print(f"[DBG] amount by label score: label='{best[3]}' value='{best[4]}' -> {best[2]}")
        return best[2]

    sweep = []
    for it in att:
        value = it.get("value_text") or ""
        conf = float(it.get("value_conf", 0.0))
        amt = extract_brl_amount(value)
        if amt is not None:
            sweep.append((conf, amt, it.get("label_text"), value))
    if sweep:
        sweep.sort(key=lambda x: x[0], reverse=True)
        best = sweep[0]
        if DEBUG:
            print(f"[DBG] amount by sweep: label='{best[2]}' value='{best[3]}' -> {best[1]}")
        return best[1]

    if DEBUG:
        print("[DBG] amount not found")
    return None


def find_installments(att: List[Dict[str, Any]]) -> Tuple[Optional[int], Optional[int]]:
    """
    Extrai (current, total) APENAS de padrões 'n/m' (aceita '/', '／' unicode, ou '-').
    - Prioriza labels com 'PLANO', 'PARCELA', 'PARCELAS'
    - Ignora 'VENCIMENTO'
    - Valida 1 <= n <= m <= 240
    """
    SEP = r"[\/\-\uFF0F]"  # barra, hífen, unicode slash (FULLWIDTH)
    RX = re.compile(rf"(\d{{1,3}})\s*{SEP}\s*(\d{{1,3}})")

    def score_label(label: str) -> int:
        L = (label or "").upper().replace("\n", " ")
        score = 0
        if "PLANO" in L:
            score += 3
        if "PARCELA" in L or "PARCELAS" in L:
            score += 2
        if "VENCIMENTO" in L:
            score -= 2
        return score

    def valid(n, m) -> bool:
        try:
            n = int(n); m = int(m)
            return 1 <= n <= m <= 240
        except Exception:
            return False

    candidates = []
    for it in att:
        label = it.get("label_text") or ""
        value = (it.get("value_text") or "")
        conf = float(it.get("value_conf", 0.0))
        m = RX.search(value)
        if not m:
            continue
        cur, total = int(m.group(1)), int(m.group(2))
        if not valid(cur, total):
            continue
        candidates.append((score_label(label), conf, cur, total, label, value))

    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best = candidates[0]
        if DEBUG:
            print(f"[DBG] installments by label score: label='{best[4]}' value='{best[5]}' -> {best[2]}/{best[3]}")
        return best[2], best[3]

    # fallback: qualquer n/m válido
    loose = []
    for it in att:
        value = (it.get("value_text") or "")
        conf = float(it.get("value_conf", 0.0))
        m = RX.search(value)
        if m:
            cur, total = int(m.group(1)), int(m.group(2))
            if valid(cur, total):
                loose.append((conf, cur, total, it.get("label_text"), value))
    if loose:
        loose.sort(key=lambda x: x[0], reverse=True)
        best = loose[0]
        if DEBUG:
            print(f"[DBG] installments by sweep: label='{best[3]}' value='{best[4]}' -> {best[1]}/{best[2]}")
        return best[1], best[2]

    if DEBUG:
        print("[DBG] installments not found")
    return None, None


def find_company(att: List[Dict[str, Any]]) -> Optional[str]:
    """
    Captura nome de banco/empresa; prioriza termos-chave.
    """
    key_re = re.compile(r"\b(Banco|BANCO|BV|Votorantim)\b", re.IGNORECASE)
    best = None  # (conf, text)
    for it in att:
        v = (it.get("value_text") or "").strip()
        if not v:
            continue
        if key_re.search(v):
            conf = float(it.get("value_conf", 0.0))
            clean = " ".join(v.split())
            if best is None or conf > best[0]:
                best = (conf, clean)
    if best and DEBUG:
        print(f"[DBG] company by sweep: '{best[1]}'")
    return best[1] if best else None


def tiny_fallback(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback determinístico mínimo (sem LLM) só para garantir algo útil.
    """
    att: List[Dict[str, Any]] = payload.get("attachment_parsed", []) or []
    cur, total = find_installments(att)
    amount = find_amount(att)
    company = find_company(att)
    return {
        "company": company,
        "installment_count": total,
        "current_installment_number": cur,
        "installment_amount": amount,
    }


def send_json(k: KafkaJSON, topic: str, obj: Dict[str, Any]) -> None:
    """
    Compatibiliza clientes que expõem k.send(...) ou k.publish(...).
    """
    if hasattr(k, "send"):
        k.send(topic, obj)
    elif hasattr(k, "publish"):
        k.publish(topic, obj)
    else:
        raise AttributeError("KafkaJSON não possui 'send' nem 'publish'.")


SYSTEM = "Você extrai dados de boletos/contratos. Responda apenas JSON válido."
USER_TPL = """Você é um extrator de dados de documentos bancários.

Abaixo está uma lista compacta de campos OCR:
cada item tem "label" (título) e "value" (valor).

Extraia APENAS os campos:
{{
  "company": string|null,
  "installment_amount": float|null
}}

Regras:
- "installment_amount" é o valor da parcela (ex.: "630,62" → 630.62);
  normalmente vem de labels como "VALOR DO DOCUMENTO", "DOCUMENTO VALOR DO", "VALOR PARCELA".
- Converta vírgula decimal brasileira para ponto.
- "company" é o nome do banco/financeira (ex.: "Banco Votorantim").
- Não invente valores; se não tiver, use null.
- Responda APENAS o JSON pedido, sem texto extra.

Campos OCR:
{payload}
"""

def prepare_reduced_ocr(payload: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    att = payload.get("attachment_parsed", []) or []
    reduced = []
    for it in att:
        label = it.get("label_text")
        value = it.get("value_text")
        if value:
            lab_norm = None if label is None else " ".join(str(label).split())
            val_norm = " ".join(str(value).split())
            reduced.append({"label": lab_norm, "value": val_norm})
    return reduced


def call_llm(payload: Dict[str, Any], llm: LLMWrapper) -> Optional[Dict[str, Any]]:
    """
    Usa seu LLMWrapper.generate() e tenta extrair JSON com: company, installment_amount.
    Parcelas NÃO vêm da LLM aqui.
    """
    try:
        reduced = prepare_reduced_ocr(payload)
        txt = llm.generate(
            prompt=USER_TPL.format(payload=json.dumps(reduced, ensure_ascii=False, indent=2)),
            system_prompt=SYSTEM,
        )
        data = LLMWrapper.extract_json(txt)
        if not data:
            if DEBUG:
                print("[DBG] LLM returned no JSON")
            return None

        # normaliza installment_amount se vier string BR
        if isinstance(data.get("installment_amount"), str):
            data["installment_amount"] = extract_brl_amount(data["installment_amount"])

        # tipos finais
        if data.get("installment_amount") is not None:
            try:
                data["installment_amount"] = float(data["installment_amount"])
            except (ValueError, TypeError):
                data["installment_amount"] = None

        out = {
            "company": data.get("company"),
            "installment_amount": data.get("installment_amount"),
        }
        if DEBUG:
            print(f"[DBG] LLM out: {out}")
        return out
    except Exception as e:
        if DEBUG:
            print(f"[DBG] LLM error: {e}")
        return None



def build_output(input_obj: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_id": int(input_obj.get("source_id", 0)),
        "agent_analysis": {
            "company": analysis.get("company"),
            "installment_count": analysis.get("installment_count"),
            "current_installment_number": analysis.get("current_installment_number"),
            "installment_amount": analysis.get("installment_amount"),
        },
        "timestamp": int(input_obj.get("timestamp", 0)),
    }


def make_handler(k: KafkaJSON, llm: LLMWrapper) -> Callable[[str, Dict[str, Any]], None]:
    """
    on_msg(topic, data) no formato que seu KafkaJSON.loop espera.
    - LLM só tenta company/amount
    - parcelas exclusivamente via regex validada
    """
    def on_msg(topic: str, data: Dict[str, Any]) -> None:
        att = data.get("attachment_parsed", []) or []

        # 1) determinístico primeiro (garante algo mesmo se LLM cair)
        det = tiny_fallback(data)

        # 2) parcelas SEMPRE de regex n/m
        cur, total = find_installments(att)
        if not (isinstance(cur, int) and isinstance(total, int) and 1 <= cur <= total <= 240):
            cur, total = None, None

        # 3) LLM (opcional) melhora company/amount; se falhar, fica det
        ia = call_llm(data, llm) or {}
        company = ia.get("company") or det.get("company")
        amount = ia.get("installment_amount") if ia.get("installment_amount") is not None else det.get("installment_amount")

        result = {
            "company": company,
            "installment_count": total,
            "current_installment_number": cur,
            "installment_amount": amount,
        }
        out = build_output(data, result)
        send_json(k, OUTPUT_TOPIC, out)
        if DEBUG:
            print(f"[DBG] final result: {result}")
        print("[OK]", out)

    return on_msg


def main():
    llm = LLMWrapper(
        provider=LLM_PROVIDER,
        model=OLLAMA_MODEL,
        temperature=LLM_TEMPERATURE,
        ollama_base_url=OLLAMA_BASE_URL,
    )

    
    k = KafkaJSON(KAFKA_BOOTSTRAP, GROUP_ID)
    k.subscribe(INPUT_TOPIC)

    k.loop(make_handler(k, llm))


if __name__ == "__main__":
    main()
