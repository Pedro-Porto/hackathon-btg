import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from provide.database import Database

app = Flask(__name__)
CORS(app)
db = Database()


@app.route("/api/offers", methods=["GET"])
def get_all_offers():
    try:
        offers = db.fetchall(
            """
            SELECT 
                bfo.id,
                b.name as bank_name,
                bfo.user_id,
                bfo.month,
                bfo.year,
                bfo.asset_value,
                bfo.monthly_interest_rate,
                bfo.total_value_with_interest,
                bfo.installments_count,
                bfo.type,
                bfo.offered,
                bfo.offered_interest_rate,
                bfo.offer_id,
                bfo.financed_amount,
                bfo.savings_amount,
                bfo.created_at
            FROM bank_financing_offers bfo
            LEFT JOIN banks b ON bfo.bank_id = b.id
            ORDER BY bfo.created_at DESC
            """
        )
        
        return jsonify({
            "status": "success",
            "count": len(offers),
            "offers": offers
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/health", methods=["GET"])
def health():
    try:
        is_healthy = db.healthcheck()
        return jsonify({
            "ok": is_healthy,
            "database": "connected" if is_healthy else "disconnected"
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3002"))
    app.run(host="0.0.0.0", port=port, debug=True)

