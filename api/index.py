# import os
from flask import Flask, request, jsonify
# from binance.client import Client
# from dotenv import load_dotenv

# load_dotenv()
app = Flask(__name__)

# Binance API Configuration
# API_KEY = os.getenv(
#     '40a30a4621ab05c3dd7611ff2e527f12e06112a36a3905313acdfef28a607244')
# API_SECRET = os.getenv(
#     'e213ec3648ff906878f3a5588e68321ec87f9b9421b9a9b4b4a5514cb2e8d3f3')
# client = Client('40a30a4621ab05c3dd7611ff2e527f12e06112a36a3905313acdfef28a607244',
#                 'e213ec3648ff906878f3a5588e68321ec87f9b9421b9a9b4b4a5514cb2e8d3f3',
#                 tld="com", testnet=True)
# client.API_URL = 'https://testnet.binancefuture.com'


@app.route("/")
def home():
    return "HELLO WORLD from VERCEL by Flask2 !"


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.get_json()

    # Extract relevant information from the TradingView alert
    symbol = data["symbol"]
    action = data["action"]  # "buy" or "sell"
    quantity = data["quantity"]
    price = data["price"]

    # if action == "buy":
    #     # Place a buy order
    #     order = client.futures_create_order(
    #         symbol=symbol,
    #         side=Client.SIDE_BUY,
    #         type=Client.ORDER_TYPE_MARKET,
    #         quantity=quantity
    #     )
    #     return jsonify({"message": "Buy order placed", "order": order})

    # elif action == "sell":
    #     # Place a sell order
    #     order = client.futures_create_order(
    #         symbol=symbol,
    #         side=Client.SIDE_SELL,
    #         type=Client.ORDER_TYPE_MARKET,
    #         quantity=quantity
    #     )
    #     return jsonify({"message": "Sell order placed", "order": order})

    return jsonify({"message": "Unknown action"})


# if __name__ == "__main__":
#     app.run(debug=True)
    # symbol = "BTCUSDT"
    # order = client.futures_create_order(
    #     symbol=symbol,
    #     side=Client.SIDE_SELL,
    #     type=Client.ORDER_TYPE_MARKET,
    #     quantity=0.01
    # )
