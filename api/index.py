import os
from flask import Flask, request, jsonify
from binance.client import Client
from dotenv import load_dotenv

load_dotenv()
app = Flask("binance_webhook")

# Binance API Configuration
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
client = Client(API_KEY, API_SECRET, tld="com", testnet=True)
client.API_URL = 'https://testnet.binancefuture.com'


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.get_json()

    # Extract relevant information from the TradingView alert
    symbol = data["symbol"]
    action = data["action"]  # "buy" or "sell"
    quantity = data["quantity"]
    price = data["price"]

    if action == "buy":
        # Place a buy order
        order = client.futures_create_order(
            symbol=symbol,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity
        )
        return jsonify({"message": "Buy order placed", "order": order})

    elif action == "sell":
        # Place a sell order
        order = client.futures_create_order(
            symbol=symbol,
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity
        )
        return jsonify({"message": "Sell order placed", "order": order})

    return jsonify({"message": "Unknown action"})


if __name__ == "__main__":
    app.run(debug=True)
    # symbol = "BTCUSDT"
    # order = client.futures_create_order(
    #     symbol=symbol,
    #     side=Client.SIDE_SELL,
    #     type=Client.ORDER_TYPE_MARKET,
    #     quantity=0.01
    # )
