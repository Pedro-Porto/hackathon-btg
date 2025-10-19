# file: core/enricher.py
from typing import Optional, List, Dict, Any
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.database import Database


class DatabaseEnricher:
    def __init__(self, db: Database):
        self.db = db
        print("✅ DatabaseEnricher inicializado com pool ativo.")

    # --------------------------
    # Métodos de consulta
    # --------------------------
    def get_user_id_from_source(self, source_id: int) -> Optional[int]:
        try:
            sql = "SELECT user_id FROM user_source WHERE source_id = %s"
            return self.db.fetchval(sql, (source_id,))
        except Exception as e:
            print(f"[ERRO] get_user_id_from_source: {e}")
            return None

    def get_user_metadata(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            sql = "SELECT user_id, full_name FROM users WHERE user_id = %s"
            row = self.db.fetchone(sql, (user_id,))
            if not row:
                return None
            return {"id": row["user_id"], "full_name": row["full_name"]}
        except Exception as e:
            print(f"[ERRO] get_user_metadata: {e}")
            return None

    def get_account_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            sql = """
                SELECT balance, credit_limit, credit_usage
                FROM accounts
                WHERE user_id = %s
                LIMIT 1
            """
            row = self.db.fetchone(sql, (user_id,))
            if not row:
                return None
            return {
                "balance": float(row.get("balance") or 0.0),
                "credit_limit": float(row.get("credit_limit") or 0.0),
                "credit_usage": float(row.get("credit_usage") or 0.0),
            }
        except Exception as e:
            print(f"[ERRO] get_account_data: {e}")
            return None

    def get_transactions(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            sql = """
                SELECT transaction_id,
                       EXTRACT(EPOCH FROM transaction_ts)::bigint AS transaction_ts,
                       transaction_type,
                       amount,
                       description
                FROM transactions
                WHERE user_id = %s
                ORDER BY transaction_ts DESC
            """
            rows = self.db.fetchall(sql, (user_id,))
            return [
                {
                    "transaction_id": r["transaction_id"],
                    "transaction_ts": int(r["transaction_ts"]),
                    "transaction_type": r["transaction_type"],
                    "amount": float(r["amount"] or 0.0),
                    "description": r["description"] or "",
                }
                for r in rows
            ]
        except Exception as e:
            print(f"[ERRO] get_transactions: {e}")
            return []

    def get_investments(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            sql = """
                SELECT i.investment_id,
                       i.investment_name,
                       i.invested_amount,
                       EXTRACT(EPOCH FROM i.invested_at)::bigint AS invested_at
                FROM investments i
                JOIN accounts a ON i.account_id = a.account_id
                WHERE a.user_id = %s
                ORDER BY i.invested_at DESC
            """
            rows = self.db.fetchall(sql, (user_id,))
            return [
                {
                    "investment_id": r["investment_id"],
                    "investment_name": r["investment_name"] or "",
                    "invested_amount": int(r["invested_amount"] or 0),
                    "invested_at": int(r["invested_at"]),
                }
                for r in rows
            ]
        except Exception as e:
            print(f"[ERRO] get_investments: {e}")
            return []

    def close(self):
        print("Encerrando pool de conexões...")
        self.db.close()
