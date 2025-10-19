from typing import Optional, Dict, Any, List
from core.database import Database


class DatabaseMatcher:
    
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.db = Database(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print(f"✅ PostgreSQL DatabaseMatcher conectado em {host}:{port}/{database}")
    
    def find_best_offer(
        self, 
        financing_type: str, 
        current_rate: float, 
        remaining_amount: float
    ) -> Optional[Dict[str, Any]]:
        try:
            current_rate_decimal = current_rate / 100
            print(f"🔍 Procurando oferta: tipo={financing_type}, taxa_atual={current_rate}% ({current_rate_decimal}), saldo={remaining_amount}")

            result = self.db.fetchone(
                """
                SELECT id, name, tax_mes, max_amount, type
                FROM financing_types
                WHERE LOWER(type) = LOWER(%s)
                AND tax_mes < %s
                AND max_amount >= %s
                ORDER BY tax_mes ASC
                LIMIT 1
                """,
                (financing_type, current_rate_decimal, remaining_amount)
            )

            print(f"📊 Resultado da query: {result}")

            if result:
                return {
                    "id": result["id"],
                    "name": result["name"],
                    "tax_mes": float(result["tax_mes"]),
                    "max_amount": float(result["max_amount"]),
                    "type": result["type"],
                }
            return None

        except Exception as e:
            print(f"❌ Erro ao buscar melhor oferta: {e}")
            return None
    
    def get_all_banks(self) -> List[Dict[str, Any]]:
        try:
            results = self.db.fetchall("SELECT id, name FROM banks ORDER BY name")
            print(f"🏦 Bancos encontrados: {len(results)}")
            return results or []
        except Exception as e:
            print(f"❌ Erro ao buscar bancos: {e}")
            return []

    def update_bank_financing_offer(
        self,
        bank_id: int,
        user_id: int,
        asset_value: float,
        monthly_interest_rate: float,
        total_value_with_interest: float,
        installments_count: int,
        financing_type: str,
        offered: bool,
        offered_interest_rate: Optional[float] = None,
        offer_id: Optional[str] = None,
        financed_amount: Optional[float] = None,
        savings_amount: Optional[float] = None
    ) -> Optional[int]:
        try:
            print(f"💾 Atualizando oferta para banco {bank_id}, usuário {user_id}...")

            with self.db.transaction() as cur:
                cur.execute(
                    """
                    UPDATE bank_financing_offers 
                    SET asset_value = %s,
                        monthly_interest_rate = %s,
                        total_value_with_interest = %s,
                        type = %s,
                        offered = %s,
                        offered_interest_rate = %s,
                        offer_id = %s,
                        financed_amount = %s,
                        savings_amount = %s
                    WHERE id = (
                        SELECT id 
                        FROM bank_financing_offers
                        WHERE bank_id = %s 
                        AND user_id = %s
                        AND installments_count = %s
                        AND offered = FALSE
                        ORDER BY created_at DESC
                        LIMIT 1
                    )
                    RETURNING id
                    """,
                    (
                        asset_value, monthly_interest_rate, total_value_with_interest,
                        financing_type, offered,
                        offered_interest_rate, offer_id, financed_amount, savings_amount,
                        bank_id, user_id, installments_count
                    )
                )
                result = cur.fetchone()

            if result:
                offer_id = result["id"] if isinstance(result, dict) else result[0]
                print(f"✅ Oferta atualizada: id={offer_id}")
                return offer_id
            else:
                print(f"⚠️ Nenhuma oferta encontrada para atualizar (bank_id={bank_id}, user_id={user_id})")
                return None

        except Exception as e:
            print(f"❌ Erro ao atualizar oferta: {e}")
            return None
    
    def close(self):
        self.db.close()
        print("🔒 Conexão com o banco encerrada")
