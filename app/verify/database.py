from typing import Optional, List, Dict, Any
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.database import Database


class DatabaseManager:
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        *,
        minconn: int = 1,
        maxconn: int = 10,
        use_dict_cursor: bool = True,
    ):
        self.db = Database(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            minconn=minconn,
            maxconn=maxconn,
            use_dict_cursor=use_dict_cursor,
        )
        print(f"✅ DatabaseManager conectado em {host}:{port}/{database}")

    def get_user_id_from_source(self, source_id: int) -> Optional[int]:
        try:
            return self.db.fetchval(
                "SELECT user_id FROM user_source WHERE source_id = %s",
                (source_id,),
            )
        except Exception as e:
            print(f"❌ Erro ao buscar user_id: {e}")
            return None

    def check_matching_transaction(self, user_id: int, installment_amount: float) -> bool:
        try:
            cnt = self.db.fetchval(
                """
                SELECT COUNT(*)
                FROM transactions
                WHERE user_id = %s
                  AND ABS(amount - %s) < 0.01
                  AND transaction_type = 'boleto'
                """,
                (user_id, installment_amount),
            )
            return bool(cnt and cnt > 0)
        except Exception as e:
            print(f"❌ Erro ao verificar transações: {e}")
            return False

    def get_all_banks(self) -> List[Dict[str, Any]]:
        try:
            rows = self.db.fetchall("SELECT id, name FROM banks ORDER BY name")
            print(f"🏦 {len(rows)} bancos encontrados")
            return rows or []
        except Exception as e:
            print(f"❌ Erro ao buscar bancos: {e}")
            return []

    def add_bank(self, name: str) -> Optional[int]:
        try:
            self.db.execute(
                "INSERT INTO banks (name) VALUES (%s)",
                (name,)
            )
            
            result = self.db.fetchone(
                "SELECT id FROM banks WHERE name = %s ORDER BY id DESC LIMIT 1",
                (name,)
            )
            
            if result:
                bank_id = result['id'] if isinstance(result, dict) else result[0]
                print(f"✅ Novo banco adicionado: {name} (id={bank_id})")
                return bank_id
            return None
        except Exception as e:
            print(f"❌ Erro ao adicionar banco: {e}")
            return None

    def insert_bank_financing_offer(
        self,
        bank_id: int,
        user_id: int,
        month: int,
        year: int,
        installments_count: int,
    ) -> Optional[int]:
        try:
            existing_id = self.db.fetchval(
                """
                SELECT id FROM bank_financing_offers
                WHERE bank_id = %s
                  AND user_id = %s
                  AND month = %s
                  AND year = %s
                  AND installments_count = %s
                LIMIT 1
                """,
                (bank_id, user_id, month, year, installments_count),
            )
            
            if existing_id is not None:
                print(f"Oferta de financiamento já existe: id={existing_id} (não duplicando)")
                return existing_id
            
            self.db.execute(
                """
                INSERT INTO bank_financing_offers
                    (bank_id, user_id, month, year,
                     asset_value, monthly_interest_rate, total_value_with_interest,
                     installments_count, type)
                VALUES (%s, %s, %s, %s,
                        0, 0, 0,
                        %s, 'UNKNOWN')
                """,
                (bank_id, user_id, month, year, installments_count)
            )
            
            result = self.db.fetchone(
                """
                SELECT id FROM bank_financing_offers
                WHERE bank_id = %s AND user_id = %s AND month = %s AND year = %s AND installments_count = %s
                ORDER BY id DESC LIMIT 1
                """,
                (bank_id, user_id, month, year, installments_count)
            )
            
            if result:
                offer_id = result['id'] if isinstance(result, dict) else result[0]
                print(f"✅ Oferta de financiamento inserida: id={offer_id}")
                return offer_id
            return None
        except Exception as e:
            print(f"❌ Erro ao inserir oferta de financiamento: {e}")
            return None

    def close(self):
        try:
            self.db.close()
            print("🔒 Conexão com o banco encerrada")
        except Exception as e:
            print(f"⚠️ Falha ao fechar pool: {e}")
