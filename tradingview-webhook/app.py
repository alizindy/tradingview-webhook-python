from chalice import Chalice
# from binance.client import Client
from binance.um_futures import UMFutures
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import time
import http.client
import json
import requests

app = Chalice(app_name='tradingview-webhook')

data = [
    {"key": 'uiTblJmq60Hjege6KTXLw9ANMdOnWSPxIp8I56Gp6FORHvk5M768DxP31yTLlxSj',
        "secret": "bWqeK7VLxsaXf2gBF5dA6EynVX7A825vYmwoMdY2rUyTmnytuJV4xbTspcAdpkax"},
    {"key": 'bVXg4acFCMdpqbXZNhoLQyw3VgqNekfKLlEzZk9NGrmWvXd6iWyS9kQjyPQIOnxB',
        "secret": "w5xL8MSwYnsNgkLNlxUw6bpJIPC1MWxak7NPLsDz6WK8nuQ0QgPNyREyrq2ShQqD"},
    {"key": 'jtvE5jrzTIIjcJu6M9t2ic72pTOci745md4G31h92q6DFG5Osmd4sLTmDbNtGKBI',
        "secret": "4Vq1tS8wmv8yDfar7z7gQp7UmEU8kKus9GCVmmWXFzGiXifHlTEXcnHpozkZ5elT"},
    {"key": 'NdkAXr3jEiUdaA6uUmy19mhUBeexiTqtEWVwTpNTW3NWiQM3AxutUbo2dYGi9OM7',
     "secret": 'VgW5tyci24xUwVJU5odxsj4leUiREDKzbDCXJEbhROFEoomQO2wLHdJTrgPiyfSW'}
]


@app.route('/')
def index():
    return {'hello': 'world'}


@app.route('/check_time_ms')
def check_time_ms():
    current_milliseconds = int(time.time() * 1000)
    current_second = current_milliseconds / 1000.0
    current_date = datetime.utcfromtimestamp(
        current_second).strftime('%Y-%m-%d %H:%M')
    url = 'https://fapi.binance.com/fapi/v1/time'
    response = requests.get(url)
    servertime_ms = 0
    servertime_date = ""
    if response.status_code == 200:
        data = response.json()
        servertime_ms = data['serverTime']
        servertime_second = servertime_ms / 1000.0
        servertime_date = datetime.utcfromtimestamp(
            servertime_second).strftime('%Y-%m-%d %H:%M')

    return {'current_ms': current_milliseconds, 'current_date': current_date, 'servertime_ms': servertime_ms, 'servertime_date': servertime_date}


def cors_preflight():
    return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}}


@app.route('/check-history-position', methods=['POST', 'OPTION'], cors=True)
def check_history_position():
    request = app.current_request
    message = request.json_body
    symbol = "ETHUSDT"

    start_time_str = message.get('start_time')
    end_time_str = message.get('end_time')

    if start_time_str is not None:
        start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        startTime = int(start_time.timestamp() * 1000)
        endTime = int(end_time.timestamp() * 1000)
        print(start_time_str)
        print(end_time)
    else:
        start_time = None
        end_time = None

    api_use = None
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])
    if start_time_str is not None:
        return client.get_account_trades(symbol=symbol, startTime=startTime, endTime=endTime)
    else:
        return client.get_account_trades(symbol=symbol, limit=1000)


@app.route('/testing_place_stopprice', methods=["POST"])
def testing_place_stopprice():

    request = app.current_request
    message = request.json_body
    symbol = "ETHUSDT"

    api_use = None
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])

    balance = client.balance()
    position_risk = client.get_position_risk(symbol=symbol)
    usdt_b = list(filter(lambda x: x['asset'] == "USDT", balance))[
        0]['balance']
    usdt_p_l = list(filter(
        lambda x: x['symbol'] == symbol and x['positionSide'] == "LONG", position_risk))
    usdt_p_s = list(filter(
        lambda x: x['symbol'] == symbol and x['positionSide'] == "SHORT", position_risk))

    current_milliseconds = int(time.time() * 1000)
    order_history = client.get_all_orders(
        symbol=symbol, startTime=current_milliseconds-(1000*60*60*24))
    new_orders = []
    filled_orders = []

    minute_limit = 5
    max_profit_check = 0.1
    unRealizedProfitPercent = 0
    openorder = "LONG" if abs(float(usdt_p_l[0]["positionAmt"])) > 0 else (
        "SHORT" if abs(float(usdt_p_s[0]["positionAmt"])) > 0 else "")
    # if isinstance(order_history, list) and len(order_history) > 0:
    #     new_orders = [
    #         order for order in order_history if (order.get("status") == "NEW" or order.get("status") == "CANCELED")]
    #     filled_orders = [
    #         order for order in order_history if order.get("status") == "FILLED"]
    #     if len(filled_orders) > 0:
    #         if abs(float(usdt_p_l[0]["positionAmt"])) > 0 or abs(float(usdt_p_s[0]["positionAmt"])) > 0:
    #             if len(filled_orders) > 0 and current_milliseconds - filled_orders[-1]["time"] > (minute_limit*60*1000):
    #                 if abs(float(usdt_p_l[0]["positionAmt"])) > 0 or abs(float(usdt_p_s[0]["positionAmt"])) > 0:
    #                     unRealizedProfit = float(usdt_p_l[0]["unRealizedProfit"]) if abs(float(
    #                         usdt_p_l[0]["positionAmt"])) > 0 else float(usdt_p_s[0]["unRealizedProfit"])
    #                     isolatedWallet = float(usdt_p_l[0]["isolatedWallet"]) if abs(float(
    #                         usdt_p_l[0]["positionAmt"])) > 0 else float(usdt_p_s[0]["isolatedWallet"])
    #                     if isolatedWallet > 0:
    #                         unRealizedProfitPercent = unRealizedProfit * \
    #                             100 / isolatedWallet

    # if unRealizedProfitPercent > max_profit_check:
    #     if len(new_orders) > 0 and new_orders[-1]['status'] == "NEW":
    #         last_stop_price = float(new_orders[-1]['stopPrice'])
    #         if openorder == "LONG":
    #             closeprice = (float(usdt_p_l[0]['markPrice']) +
    #                           float(usdt_p_l[0]['entryPrice']))*0.5
    #             if closeprice > last_stop_price:
    #                 client.cancel_open_orders(symbol=symbol)
    #                 client.new_order(symbol=symbol, positionSide="LONG", side="SELL", stopPrice=int(closeprice),
    #                                  type="STOP_MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
    #         if openorder == "SHORT":
    #             closeprice = (float(usdt_p_s[0]['markPrice']) +
    #                           float(usdt_p_s[0]['entryPrice']))*0.5
    #             if closeprice < last_stop_price:
    #                 client.cancel_open_orders(symbol=symbol)
    #                 client.new_order(symbol=symbol, positionSide="SHORT", side="BUY", stopPrice=int(closeprice),
    #                                  type="STOP_MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))
    #     elif len(new_orders) == 0 or new_orders[-1]['status'] == "CANCELED":
    #         if openorder == "LONG":
    #             closeprice = (float(usdt_p_l[0]['markPrice']) +
    #                           float(usdt_p_l[0]['entryPrice']))*0.5
    #             client.new_order(symbol=symbol, positionSide="LONG", side="SELL", stopPrice=int(closeprice),
    #                              type="STOP_MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
    #         if openorder == "SHORT":
    #             closeprice = (float(usdt_p_s[0]['markPrice']) +
    #                           float(usdt_p_s[0]['entryPrice']))*0.5
    #             client.new_order(symbol=symbol, positionSide="SHORT", side="BUY", stopPrice=int(closeprice),
    #                              type="STOP_MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))

    return {
        'order_history': order_history,
        'new_orders': new_orders,
        'difference_time': 0 if len(filled_orders) == 0 else current_milliseconds - filled_orders[-1]["time"],
        'filled_orders': filled_orders,
        'usdt_p_l': usdt_p_l,
        'usdt_p_s': usdt_p_s,
        'unRealizedProfitPercent': unRealizedProfitPercent
    }


@app.route("/get-account-balance", methods=["GET"])
def get_account_balance():
    client = UMFutures('bVXg4acFCMdpqbXZNhoLQyw3VgqNekfKLlEzZk9NGrmWvXd6iWyS9kQjyPQIOnxB',
                       'w5xL8MSwYnsNgkLNlxUw6bpJIPC1MWxak7NPLsDz6WK8nuQ0QgPNyREyrq2ShQqD')

    balance = client.balance()
    position_risk = client.get_position_risk(symbol="ETHUSDT")
    usdt_b = list(filter(lambda x: x['asset'] == "USDT", balance))[
        0]['balance']
    usdt_p_l = list(filter(
        lambda x: x['symbol'] == "ETHUSDT" and x['positionSide'] == "LONG", position_risk))
    usdt_p_s = list(filter(
        lambda x: x['symbol'] == "ETHUSDT" and x['positionSide'] == "SHORT", position_risk))

    minqty = round(
        (0.004*(float(usdt_p_l[0]['markPrice']))/float(usdt_b))*0.3, 3)

    return {
        'balance': float(str(usdt_b)),
        'position_long': usdt_p_l[0],
        'position_short': usdt_p_s[0],
        'minqty': minqty
    }


@app.route("/get-account-balance-info", methods=["POST"])
def get_account_balance_info():

    request = app.current_request
    message = request.json_body

    api_use = None
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])

    balance = client.balance()
    position_risk = client.get_position_risk(symbol="ETHUSDT")
    usdt_b = list(filter(lambda x: x['asset'] == "USDT", balance))[
        0]['balance']
    usdt_p_l = list(filter(
        lambda x: x['symbol'] == "ETHUSDT" and x['positionSide'] == "LONG", position_risk))
    usdt_p_s = list(filter(
        lambda x: x['symbol'] == "ETHUSDT" and x['positionSide'] == "SHORT", position_risk))

    if len(usdt_p_l) > 0:
        minqty = 0 if float(usdt_b) == 0 else round(
            (0.004*(float(usdt_p_l[0]['markPrice']))/float(usdt_b))*0.3, 3)
    else:
        minqty = 0

    position_history = client.get_position_margin_history(
        symbol="ETHUSDT")
    timefulls = [item['time'] for item in position_history]
    timeeach = list(
        map(lambda x: (datetime.utcfromtimestamp(x/1000)).strftime('%Y-%m-%d %H:%M'), timefulls))

    return {
        'balance': float(str(usdt_b)),
        'position_long': usdt_p_l,
        'position_short': usdt_p_s,
        'position_time': timefulls,
        'position_history': str(timeeach),
        'minqty': minqty
    }


# @app.route("/order-MRMFRS-v1", methods=["POST"])
# def order_1():

#     request = app.current_request
#     message = request.json_body

#     api_use = None
#     for obj in data:
#         if 'key' in obj and obj['key'] == message['key']:
#             api_use = obj
#             break

#     client = UMFutures(api_use['key'], api_use['secret'])

#     leverage = 1
#     symbol = message['symbol']
#     balance = client.balance()
#     position_risk = client.get_position_risk(symbol=symbol)
#     usdt_b = list(filter(lambda x: (x['asset'] == "USDT") if "USDT" in symbol else (x['asset'] == "BUSD"), balance))[
#         0]['balance']

#     usdt_p_l = list(filter(
#         lambda x: x['symbol'] == symbol and x['positionSide'] == "LONG", position_risk))
#     usdt_p_s = list(filter(
#         lambda x: x['symbol'] == symbol and x['positionSide'] == "SHORT", position_risk))

#     if len(usdt_p_l) > 0:
#         mark_price = float(message['close']) if ('close' in message and float(
#             usdt_p_l[0]['markPrice']) == 0) else float(usdt_p_l[0]['markPrice'])
#     elif len(usdt_p_s) > 0:
#         mark_price = float(message['close']) if ('close' in message and float(
#             usdt_p_s[0]['markPrice']) == 0) else float(usdt_p_s[0]['markPrice'])
#     else:
#         mark_price = 0
#     minqty = 0 if mark_price == 0 else round(
#         (float(usdt_b)*0.3) / (mark_price/leverage), 3)

#     opentrades = int(str(message['opentrades']))
#     isOpen = False

#     rsiMAState = message['rsiMAState']

#     highest = float(message['highest'])
#     lowest = float(message['lowest'])
#     high = float(message['high'])
#     low = float(message['low'])

#     s1 = float(message['s1'])
#     s3 = float(message['s3'])
#     r1 = float(message['r1'])
#     r3 = float(message['r3'])
#     rt = float(message['rt'])
#     sp = float(message['sp'])
#     pmop = float(message['pmop'])
#     s3op = float(message['s3op'])
#     r3op = float(message['r3op'])
#     pass_s3 = float(message['pass_s3'])
#     pass_r3 = float(message['pass_r3'])
#     pmeanline = float(message['pmeanline'])

#     current_milliseconds = int(time.time() * 1000)
#     order_history = client.get_all_orders(
#         symbol=symbol, startTime=current_milliseconds-(1000*60*60*24))
#     new_orders = []
#     filled_orders = []

#     minute_limit = 5
#     max_profit_check = 0.6
#     unRealizedProfitPercentLongCheck = 0
#     unRealizedProfitPercentShortCheck = 0
#     unRealizedProfitPercentLong = 0
#     unRealizedProfitPercentShort = 0

#     openorderLong = abs(float(usdt_p_l[0]["positionAmt"])) > 0
#     lastopenLongTime = 0
#     openorderShort = abs(float(usdt_p_s[0]["positionAmt"])) > 0
#     lastopenShortTime = 0

#     # LONG_STOP_PRICE
#     if isinstance(order_history, list) and len(order_history) > 0 and openorderLong:
#         new_orders = [
#             order for order in order_history if ((order.get("status") == "NEW" or order.get("status") == "CANCELED") and order.get("positionSide") == "LONG")]
#         filled_orders = [
#             order for order in order_history if (order.get("status") == "FILLED" and order.get("positionSide") == "LONG")]
#         if len(filled_orders) > 0:
#             lastopenLongTime = filled_orders[-1]["time"]
#             if len(filled_orders) > 0 and current_milliseconds - filled_orders[-1]["time"] > (minute_limit*60*1000):
#                 unRealizedProfit = float(usdt_p_l[0]["unRealizedProfit"])
#                 isolatedWallet = float(usdt_p_l[0]["isolatedWallet"])
#                 if isolatedWallet > 0:
#                     unRealizedProfitPercentLong = unRealizedProfit * \
#                         100 / isolatedWallet

#     # SHORT_STOP_PRICE
#     if isinstance(order_history, list) and len(order_history) > 0 and openorderShort:
#         new_orders = [
#             order for order in order_history if ((order.get("status") == "NEW" or order.get("status") == "CANCELED") and order.get("positionSide") == "SHORT")]
#         filled_orders = [
#             order for order in order_history if (order.get("status") == "FILLED" and order.get("positionSide") == "SHORT")]
#         if len(filled_orders) > 0:
#             lastopenShortTime = filled_orders[-1]["time"]
#             if len(filled_orders) > 0 and current_milliseconds - filled_orders[-1]["time"] > (minute_limit*60*1000):
#                 unRealizedProfit = float(usdt_p_s[0]["unRealizedProfit"])
#                 isolatedWallet = float(usdt_p_s[0]["isolatedWallet"])
#                 if isolatedWallet > 0:
#                     unRealizedProfitPercentShort = unRealizedProfit * \
#                         100 / isolatedWallet

#     if minqty > 0:

#         if opentrades > 0:

#             positionSide = message['positionSide']
#             barstatus = message['barstatus']

#             if 'livebar' in message:

#                 unRealizedProfitPercentOpenningShort = 0
#                 unRealizedProfitOpenningShort = float(
#                     usdt_p_s[0]["unRealizedProfit"])
#                 isolatedWalletOpenningShort = float(
#                     usdt_p_s[0]["isolatedWallet"])
#                 if isolatedWalletOpenningShort > 0:
#                     unRealizedProfitPercentOpenningShort = unRealizedProfitOpenningShort * \
#                         100 / isolatedWalletOpenningShort

#                 unRealizedProfitPercentOpenningLong = 0
#                 unRealizedProfitOpenningLong = float(
#                     usdt_p_l[0]["unRealizedProfit"])
#                 isolatedWalletOpenningLong = float(
#                     usdt_p_l[0]["isolatedWallet"])
#                 if isolatedWalletOpenningLong > 0:
#                     unRealizedProfitPercentOpenningLong = unRealizedProfitOpenningLong * \
#                         100 / isolatedWalletOpenningLong

#                 if positionSide == "LONG":

#                     # Close
#                     quantityclose = 0
#                     if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
#                         if int(message['openbar']) >= 1 or float(usdt_p_s[0]['unRealizedProfit']) > 0:
#                             if unRealizedProfitPercentOpenningShort > 0.3:
#                                 unRealizedProfitPercent = 0
#                                 unRealizedProfit = float(
#                                     usdt_p_s[0]["unRealizedProfit"])
#                                 isolatedWallet = float(
#                                     usdt_p_s[0]["isolatedWallet"])
#                                 if isolatedWallet > 0:
#                                     unRealizedProfitPercent = unRealizedProfit * \
#                                         100 / isolatedWallet
#                                 if unRealizedProfitPercent >= 0.1:
#                                     quantityclose = abs(float(
#                                         usdt_p_s[0]['positionAmt'])) if unRealizedProfitPercent <= 0.6 else round(minqty, 3)
#                             else:
#                                 if lastopenShortTime != 0 and current_milliseconds - lastopenShortTime >= 7.5*60*1000:
#                                     quantityclose = minqty

#                             if quantityclose > 0:
#                                 client.cancel_open_orders(symbol=symbol)
#                                 client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
#                                                  type="MARKET", quantity=round(quantityclose, 3))

#                     # Open
#                     if int(message['openbar']) >= 1 or abs(float(usdt_p_s[0]['positionAmt'])) == 0 or float(usdt_p_s[0]['unRealizedProfit']) > 0 or abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty*2)-0.001:
#                         if (abs(float(usdt_p_l[0]['positionAmt'])) < opentrades*minqty):
#                             if int(str(message['openbar'])) < 8 or (rsiMAState == "UP" and float(message['rsi']) > float(message['rsiMA'])) or (barstatus == "UP" and mark_price < r1) or mark_price < float(message['openprice']) or (abs(float(usdt_p_s[0]['positionAmt'])) > 0) or (abs(float(usdt_p_l[0]['positionAmt'])) == 0 and opentrades >= 2) or (abs(float(usdt_p_l[0]['positionAmt'])) == 0 and (float(message['rsi']) <= 30 or float(message['rsi15']) <= 30)):
#                                 if abs(float(usdt_p_l[0]['positionAmt'])) == 0:
#                                     client.cancel_open_orders(symbol=symbol)
#                                     client.new_order(symbol=symbol, positionSide=positionSide, side=(
#                                         "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
#                                 elif (abs(float(usdt_p_l[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
#                                     leftQty = minqty - \
#                                         abs(float(usdt_p_l[0]['positionAmt']))
#                                     client.cancel_open_orders(symbol=symbol)
#                                     client.new_order(symbol=symbol, positionSide=positionSide, side=(
#                                         "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(leftQty, 3))
#                                 elif (abs(float(usdt_p_l[0]['positionAmt'])) < 1.5*minqty and opentrades >= 2):
#                                     if s3 > pmop or r3 < pmop or float(message['rsi']) <= 30 or (opentrades > 2 and (float(message['rsi']) <= 50 or mark_price < pmeanline)) or (pass_s3 and mark_price < s1) or float(message['rsiMA']) <= 30 or unRealizedProfitPercentOpenningLong >= 1.2 or (unRealizedProfitPercentOpenningShort < -0.6):
#                                         # if float(message['rsi15']) <= 30 or float(message['rsiMA15']) <= 30 or opentrades > 2 or mark_price < s3 or (unRealizedProfitPercentOpenningLong >= 0.6 and mark_price > r1):
#                                         client.new_order(symbol=symbol, positionSide=positionSide, side=(
#                                             "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
#                                 elif (abs(float(usdt_p_l[0]['positionAmt'])) < 2.5*minqty and opentrades >= 3):
#                                     if s3 > r3op or r3 < s3op or unRealizedProfitPercentOpenningLong >= 1.8:
#                                         # if float(message['rsi']) <= 30 or float(message['rsiMA']) <= 30 or (unRealizedProfitPercentOpenningLong >= 0.6 and mark_price > r3):
#                                         client.new_order(symbol=symbol, positionSide=positionSide, side=(
#                                             "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))

#                 if positionSide == "SHORT":

#                     # Close
#                     quantityclose = 0
#                     if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
#                         if int(message['openbar']) >= 1 or float(usdt_p_l[0]['unRealizedProfit']) > 0:
#                             if unRealizedProfitPercentOpenningLong > 0.3:
#                                 unRealizedProfitPercent = 0
#                                 unRealizedProfit = float(
#                                     usdt_p_l[0]["unRealizedProfit"])
#                                 isolatedWallet = float(
#                                     usdt_p_l[0]["isolatedWallet"])
#                                 if isolatedWallet > 0:
#                                     unRealizedProfitPercent = unRealizedProfit * \
#                                         100 / isolatedWallet
#                                 if unRealizedProfitPercent >= 0.1:
#                                     quantityclose = abs(float(
#                                         usdt_p_l[0]['positionAmt'])) if unRealizedProfitPercent <= 0.6 else round(minqty, 3)
#                             else:
#                                 if lastopenLongTime != 0 and current_milliseconds - lastopenLongTime >= 7.5*60*1000:
#                                     quantityclose = minqty

#                             if quantityclose > 0:
#                                 client.cancel_open_orders(symbol=symbol)
#                                 client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
#                                                  type="MARKET", quantity=round(quantityclose, 3))

#                     # OPEN
#                     if int(message['openbar']) >= 1 or abs(float(usdt_p_l[0]['positionAmt'])) == 0 or float(usdt_p_l[0]['unRealizedProfit']) > 0 or abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty*2)-0.001:
#                         if (abs(float(usdt_p_s[0]['positionAmt'])) < opentrades*minqty):
#                             if int(str(message['openbar'])) < 8 or (rsiMAState == "DOWN" and float(message['rsi']) < float(message['rsiMA'])) or (barstatus == "DOWN" and mark_price > s1) or mark_price > float(message['openprice']) or (abs(float(usdt_p_l[0]['positionAmt'])) > 0) or (abs(float(usdt_p_s[0]['positionAmt'])) == 0 and opentrades >= 2) or (abs(float(usdt_p_s[0]['positionAmt'])) == 0 and (float(message['rsi']) >= 70 or float(message['rsi15']) >= 70)):
#                                 if abs(float(usdt_p_s[0]['positionAmt'])) == 0:
#                                     client.cancel_open_orders(symbol=symbol)
#                                     client.new_order(symbol=symbol, positionSide=positionSide, side=(
#                                         "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
#                                 elif (abs(float(usdt_p_s[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
#                                     leftQty = minqty - \
#                                         abs(float(usdt_p_s[0]['positionAmt']))
#                                     client.cancel_open_orders(symbol=symbol)
#                                     client.new_order(symbol=symbol, positionSide=positionSide, side=(
#                                         "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(leftQty, 3))
#                                 elif (abs(float(usdt_p_s[0]['positionAmt'])) < 1.5*minqty and opentrades >= 2):
#                                     if s3 > pmop or r3 < pmop or float(message['rsi']) >= 70 or (opentrades > 2 and (float(message['rsi']) >= 50 or mark_price > pmeanline)) or (pass_r3 and mark_price > r1) or float(message['rsiMA']) >= 70 or unRealizedProfitPercentOpenningShort >= 1.2 or (unRealizedProfitPercentOpenningLong < -0.6):
#                                         # if float(message['rsi15']) >= 70 or float(message['rsiMA15']) >= 70 or opentrades > 2 or mark_price > r3 or (unRealizedProfitPercentOpenningShort >= 0.6 and mark_price < s1):
#                                         client.new_order(symbol=symbol, positionSide=positionSide, side=(
#                                             "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
#                                 elif (abs(float(usdt_p_s[0]['positionAmt'])) < 2.5*minqty and opentrades >= 3):
#                                     if s3 > r3op or r3 < s3op or unRealizedProfitPercentOpenningShort >= 1.8:
#                                         # if float(message['rsi']) >= 70 or float(message['rsiMA']) >= 70 or (unRealizedProfitPercentOpenningShort >= 0.6 and mark_price < s3):
#                                         client.new_order(symbol=symbol, positionSide=positionSide, side=(
#                                             "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))

#         else:

#             unRealizedProfitOpenningLong = float(
#                 usdt_p_l[0]["unRealizedProfit"])
#             isolatedWalletOpenningLong = float(usdt_p_l[0]["isolatedWallet"])
#             if isolatedWalletOpenningLong > 0:
#                 unRealizedProfitPercentOpenningLong = unRealizedProfitOpenningLong * \
#                     100 / isolatedWalletOpenningLong

#             unRealizedProfitOpenningShort = float(
#                 usdt_p_s[0]["unRealizedProfit"])
#             isolatedWalletOpenningShort = float(usdt_p_s[0]["isolatedWallet"])
#             if isolatedWalletOpenningShort > 0:
#                 unRealizedProfitPercentOpenningShort = unRealizedProfitOpenningShort * \
#                     100 / isolatedWalletOpenningShort

#             # CLOSE
#             if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
#                 if unRealizedProfitOpenningLong >= 0.45 or (unRealizedProfitOpenningLong > 0 and ('forceclose' in message and float(message['forceclose']) == 2)):
#                     client.cancel_open_orders(symbol=symbol)
#                     client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
#                                      type="MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
#             if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
#                 if unRealizedProfitOpenningShort >= 0.45 or (unRealizedProfitOpenningShort > 0 and ('forceclose' in message and float(message['forceclose']) == 1)):
#                     client.cancel_open_orders(symbol=symbol)
#                     client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
#                                      type="MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))


@app.route("/order-MRMFRS", methods=["POST"])
# Mean Reversal + MACD + Fibonacci + Resistance and Support
def order_2():

    request = app.current_request
    message = request.json_body

    api_use = None
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])

    leverage = 1
    symbol = message['symbol']
    balance = client.balance()
    position_risk = client.get_position_risk(symbol=symbol)
    usdt_b = list(filter(lambda x: (x['asset'] == "USDT") if "USDT" in symbol else (x['asset'] == "BUSD"), balance))[
        0]['balance']

    usdt_p_l = list(filter(
        lambda x: x['symbol'] == symbol and x['positionSide'] == "LONG", position_risk))
    usdt_p_s = list(filter(
        lambda x: x['symbol'] == symbol and x['positionSide'] == "SHORT", position_risk))

    if len(usdt_p_l) > 0:
        mark_price = float(message['close']) if ('close' in message and float(
            usdt_p_l[0]['markPrice']) == 0) else float(usdt_p_l[0]['markPrice'])
    elif len(usdt_p_s) > 0:
        mark_price = float(message['close']) if ('close' in message and float(
            usdt_p_s[0]['markPrice']) == 0) else float(usdt_p_s[0]['markPrice'])
    else:
        mark_price = 0
    minqty = 0 if mark_price == 0 else round(
        (float(usdt_b)*0.3) / (mark_price/leverage), 3)

    opentrades = int(str(message['opentrades']))
    isOpen = False

    rsiMAState = message['rsiMAState']
    pmeanlineState = message['pmeanlineState']

    highest = float(message['highest'])
    lowest = float(message['lowest'])
    high = float(message['high'])
    low = float(message['low'])
    openprice = float(message['open'])
    close = float(message['close'])
    openbar = int(message['openbar'])

    s1 = float(message['s1'])
    s3 = float(message['s3'])
    r1 = float(message['r1'])
    r3 = float(message['r3'])
    rt = float(message['rt'])
    sp = float(message['sp'])
    pmop = float(message['pmop'])
    s3op = float(message['s3op'])
    r3op = float(message['r3op'])
    pass_s3 = float(message['pass_s3'])
    pass_r3 = float(message['pass_r3'])
    pmeanline = float(message['pmeanline'])
    highest_long = float(message['highest_long'])
    lowest_short = float(message['lowest_short'])

    winrate, lossable, winrate_margin, lossable_margin, win_margin, loss_margin = lossable_calculate(
        client, symbol)

    if minqty > 0:

        if opentrades > 0:

            positionSide = message['positionSide']
            barstatus = message['barstatus']

            if 'livebar' in message:

                unRealizedProfitPercentOpenningShort = 0
                unRealizedProfitOpenningShort = float(
                    usdt_p_s[0]["unRealizedProfit"])
                isolatedWalletOpenningShort = float(
                    usdt_p_s[0]["isolatedWallet"])
                if isolatedWalletOpenningShort > 0:
                    unRealizedProfitPercentOpenningShort = unRealizedProfitOpenningShort * \
                        100 / isolatedWalletOpenningShort

                unRealizedProfitPercentOpenningLong = 0
                unRealizedProfitOpenningLong = float(
                    usdt_p_l[0]["unRealizedProfit"])
                isolatedWalletOpenningLong = float(
                    usdt_p_l[0]["isolatedWallet"])
                if isolatedWalletOpenningLong > 0:
                    unRealizedProfitPercentOpenningLong = unRealizedProfitOpenningLong * \
                        100 / isolatedWalletOpenningLong

                if positionSide == "LONG":

                    # Close
                    quantityclose = 0
                    if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
                        if openbar >= 1 or float(usdt_p_s[0]['unRealizedProfit']) > 0:
                            if unRealizedProfitPercentOpenningShort > 0.3:
                                quantityclose = abs(float(
                                    usdt_p_s[0]['positionAmt'])) if (unRealizedProfitPercentOpenningShort <= 0.6 or abs(float(
                                        usdt_p_s[0]['positionAmt'])) < minqty) else round(minqty, 3)
                            else:
                                if (float(usdt_p_s[0]['entryPrice']) - mark_price)*minqty > lossable_margin and lossable >= 75 and (low >= r1 or high <= s1 or float(usdt_p_s[0]['entryPrice']) <= s3):
                                    quantityclose = abs(float(usdt_p_s[0]['positionAmt'])) if abs(float(
                                        usdt_p_s[0]['positionAmt'])) < minqty*1.5 else minqty
                                else:
                                    if abs(float(usdt_p_s[0]['positionAmt'])) <= minqty*1.5:
                                        if (unRealizedProfitPercentOpenningLong > abs(unRealizedProfitPercentOpenningShort)*2 and unRealizedProfitPercentOpenningLong > 1.2):
                                            if not (float(message['rsiMA15']) >= 70 or (float(message['rsiMA15']) >= 65 and float(message['rsi15']) >= 70)):
                                                quantityclose = abs(
                                                    float(usdt_p_s[0]['positionAmt']))
                                    else:
                                        if opentrades == 3:
                                            if s3 > pmop or r3 < pmop or float(message['rsi']) <= 30 or (opentrades > 2 and (float(message['rsi']) <= 50 or mark_price < pmeanline)) or (pass_s3 and mark_price < s1) or float(message['rsiMA']) <= 30 or unRealizedProfitPercentOpenningLong >= 1.2:
                                                if abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*1.5:
                                                    quantityclose = minqty
                                        if opentrades == 2:
                                            if abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*2.5:
                                                quantityclose = minqty

                            if quantityclose > 0:
                                client.cancel_open_orders(symbol=symbol)
                                client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                                 type="MARKET", quantity=round(quantityclose, 3))

                    # Open
                    if openbar >= 1 or abs(float(usdt_p_s[0]['positionAmt'])) == 0 or float(usdt_p_s[0]['unRealizedProfit']) > 0 or abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*1.5:
                        if (abs(float(usdt_p_l[0]['positionAmt'])) < opentrades*minqty):
                            if ((openbar < 8) or
                                (rsiMAState == "UP" and float(message['rsi']) > float(message['rsiMA']) and mark_price > openprice) or
                                (barstatus == "UP" and mark_price < r1 and mark_price > openprice) or
                                    (abs(float(usdt_p_l[0]['positionAmt'])) == 0 and (float(message['rsi']) <= 30 or float(message['rsiMA15']) <= 30))):
                                if abs(float(usdt_p_l[0]['positionAmt'])) == 0:
                                    client.cancel_open_orders(symbol=symbol)
                                    client.new_order(
                                        symbol=symbol, positionSide="LONG", side="BUY", type="MARKET", quantity=round(minqty, 3))
                                elif (abs(float(usdt_p_l[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
                                    leftQty = minqty - \
                                        abs(float(usdt_p_l[0]['positionAmt']))
                                    client.cancel_open_orders(symbol=symbol)
                                    client.new_order(
                                        symbol=symbol, positionSide="LONG", side="BUY", type="MARKET", quantity=round(leftQty, 3))
                                elif (abs(float(usdt_p_l[0]['positionAmt'])) < 1.5*minqty and opentrades >= 2):
                                    if ((s3 > pmop) or
                                        (r3 < pmop) or
                                        (pass_s3 and mark_price < s1) or
                                        (float(message['rsi']) <= 30) or
                                        (float(message['rsiMA']) <= 30) or
                                        (opentrades > 2 and (float(message['rsi']) <= 50 or mark_price < pmeanline)) or
                                        (unRealizedProfitPercentOpenningLong >= 1.2) or
                                            (unRealizedProfitPercentOpenningShort < -0.6 and (pmeanlineState == "UP" or rsiMAState == "UP"))):
                                        client.new_order(
                                            symbol=symbol, positionSide="LONG", side="BUY", type="MARKET", quantity=round(minqty, 3))
                                elif (abs(float(usdt_p_l[0]['positionAmt'])) < 2.5*minqty and opentrades >= 3):
                                    if ((s3 > r3op) or
                                        (r3 < s3op) or
                                            (unRealizedProfitPercentOpenningLong >= 1.8)):
                                        client.new_order(
                                            symbol=symbol, positionSide="LONG", side="BUY", type="MARKET", quantity=round(minqty, 3))

                if positionSide == "SHORT":

                    # Close
                    quantityclose = 0
                    if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
                        if openbar >= 1 or float(usdt_p_l[0]['unRealizedProfit']) > 0:
                            if unRealizedProfitPercentOpenningLong > 0.3:
                                quantityclose = abs(float(
                                    usdt_p_l[0]['positionAmt'])) if (unRealizedProfitPercentOpenningLong <= 0.6 or abs(float(
                                        usdt_p_l[0]['positionAmt'])) < minqty) else round(minqty, 3)
                            else:
                                if (mark_price - float(usdt_p_l[0]['entryPrice']))*minqty > lossable_margin and lossable >= 75 and (low >= r1 or high <= s1 or float(usdt_p_l[0]['entryPrice']) >= r3):
                                    quantityclose = abs(float(usdt_p_l[0]['positionAmt'])) if abs(float(
                                        usdt_p_l[0]['positionAmt'])) < minqty*1.5 else minqty
                                else:
                                    if abs(float(usdt_p_l[0]['positionAmt'])) <= minqty*1.5:
                                        if (unRealizedProfitPercentOpenningShort > abs(unRealizedProfitPercentOpenningLong)*2 and unRealizedProfitPercentOpenningShort > 1.2):
                                            if not (float(message['rsiMA15']) <= 30 or (float(message['rsiMA15']) <= 35 and float(message['rsi15']) <= 30)):
                                                quantityclose = abs(
                                                    float(usdt_p_l[0]['positionAmt']))
                                    else:
                                        if opentrades == 3:
                                            if s3 > pmop or r3 < pmop or float(message['rsi']) >= 70 or (opentrades > 2 and (float(message['rsi']) >= 50 or mark_price > pmeanline)) or (pass_r3 and mark_price > r1) or float(message['rsiMA']) >= 70 or unRealizedProfitPercentOpenningShort >= 1.2:
                                                if abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*1.5:
                                                    quantityclose = minqty
                                        if opentrades == 2:
                                            if abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*2.5:
                                                quantityclose = minqty

                            if quantityclose > 0:
                                client.cancel_open_orders(symbol=symbol)
                                client.new_order(
                                    symbol=symbol, positionSide="LONG", side="SELL", type="MARKET", quantity=round(quantityclose, 3))

                    # OPEN
                    if openbar >= 1 or abs(float(usdt_p_l[0]['positionAmt'])) == 0 or float(usdt_p_l[0]['unRealizedProfit']) > 0 or abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*1.5:
                        if (abs(float(usdt_p_s[0]['positionAmt'])) < opentrades*minqty):
                            if ((openbar < 8) or
                                (rsiMAState == "DOWN" and float(message['rsi']) < float(message['rsiMA']) and mark_price < openprice) or
                                (barstatus == "DOWN" and mark_price > s1 and mark_price < openprice) or
                                    (abs(float(usdt_p_s[0]['positionAmt'])) == 0 and (float(message['rsi']) >= 70 or float(message['rsiMA15']) >= 70))):
                                if abs(float(usdt_p_s[0]['positionAmt'])) == 0:
                                    client.cancel_open_orders(symbol=symbol)
                                    client.new_order(
                                        symbol=symbol, positionSide="SHORT", side="SELL", type="MARKET", quantity=round(minqty, 3))
                                elif (abs(float(usdt_p_s[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
                                    leftQty = minqty - \
                                        abs(float(usdt_p_s[0]['positionAmt']))
                                    client.cancel_open_orders(symbol=symbol)
                                    client.new_order(
                                        symbol=symbol, positionSide="SHORT", side="SELL", type="MARKET", quantity=round(leftQty, 3))
                                elif (abs(float(usdt_p_s[0]['positionAmt'])) < 1.5*minqty and opentrades >= 2):
                                    if ((s3 > pmop) or
                                        (r3 < pmop) or
                                        (pass_r3 and mark_price > r1) or
                                        (float(message['rsi']) >= 70) or
                                        (float(message['rsiMA']) >= 70) or
                                        (opentrades > 2 and (float(message['rsi']) >= 50 or mark_price > pmeanline)) or
                                        (unRealizedProfitPercentOpenningShort >= 1.2) or
                                            (unRealizedProfitPercentOpenningLong < -0.6 and (pmeanlineState == "DOWN" or rsiMAState == "DOWN"))):
                                        client.new_order(
                                            symbol=symbol, positionSide="SHORT", side="SELL", type="MARKET", quantity=round(minqty, 3))
                                elif (abs(float(usdt_p_s[0]['positionAmt'])) < 2.5*minqty and opentrades >= 3):
                                    if ((s3 > r3op) or
                                        (r3 < s3op) or
                                            (unRealizedProfitPercentOpenningShort >= 1.8)):
                                        client.new_order(
                                            symbol=symbol, positionSide="SHORT", side="SELL", type="MARKET", quantity=round(minqty, 3))

        else:

            unRealizedProfitOpenningLong = float(
                usdt_p_l[0]["unRealizedProfit"])
            isolatedWalletOpenningLong = float(usdt_p_l[0]["isolatedWallet"])
            if isolatedWalletOpenningLong > 0:
                unRealizedProfitPercentOpenningLong = unRealizedProfitOpenningLong * \
                    100 / isolatedWalletOpenningLong

            unRealizedProfitOpenningShort = float(
                usdt_p_s[0]["unRealizedProfit"])
            isolatedWalletOpenningShort = float(usdt_p_s[0]["isolatedWallet"])
            if isolatedWalletOpenningShort > 0:
                unRealizedProfitPercentOpenningShort = unRealizedProfitOpenningShort * \
                    100 / isolatedWalletOpenningShort

            # CLOSE
            if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
                if (mark_price - float(usdt_p_l[0]['entryPrice']))*minqty > lossable_margin and lossable >= 75:
                    client.cancel_open_orders(symbol=symbol)
                    client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                     type="MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
                else:
                    if unRealizedProfitOpenningLong >= 0.45 or (unRealizedProfitOpenningLong > 0 and ('forceclose' in message and float(message['forceclose']) == 2)):
                        client.cancel_open_orders(symbol=symbol)
                        client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                         type="MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
            if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
                if (float(usdt_p_s[0]['entryPrice']) - mark_price)*minqty > lossable_margin and lossable >= 75:
                    client.cancel_open_orders(symbol=symbol)
                    client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                     type="MARKET", quantity=round(minqty, 3))
                else:
                    if unRealizedProfitOpenningShort >= 0.45 or (unRealizedProfitOpenningShort > 0 and ('forceclose' in message and float(message['forceclose']) == 1)):
                        client.cancel_open_orders(symbol=symbol)
                        client.new_order(symbol=symbol, positionSide="SHORT", side="BUY", type="MARKET", quantity=abs(
                            float(usdt_p_s[0]['positionAmt'])))

        # OPPOSITE_OPEN
        if abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*1.5 and abs(float(usdt_p_s[0]['positionAmt'])) < (minqty)*2.5 and abs(float(usdt_p_l[0]['positionAmt'])) == 0:
            if (float(message['rsiMA15']) <= 30 or (float(message['rsiMA15']) <= 35 and float(message['rsi15']) <= 30)) and barstatus == "UP" and low > s3:
                client.cancel_open_orders(symbol=symbol)
                client.new_order(symbol=symbol, positionSide="LONG",
                                 side="BUY", type="MARKET", quantity=round(minqty, 3))
        if abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*1.5 and abs(float(usdt_p_l[0]['positionAmt'])) < (minqty)*2.5 and abs(float(usdt_p_s[0]['positionAmt'])) == 0:
            if (float(message['rsiMA15']) >= 70 or (float(message['rsiMA15']) >= 65 and float(message['rsi15']) >= 70)) and barstatus == "DOWN" and high < r3:
                client.cancel_open_orders(symbol=symbol)
                client.new_order(symbol=symbol, positionSide="SHORT",
                                 side="SELL", type="MARKET", quantity=round(minqty, 3))

    current_milliseconds = int(time.time() * 1000)
    order_history = client.get_all_orders(
        symbol=symbol, startTime=current_milliseconds-(1000*60*60*24))
    new_orders_long = []
    new_orders_short = []
    filled_orders = []

    minute_limit = 5
    max_profit_check = 0.6
    unRealizedProfitPercentLong = 0
    unRealizedProfitPercentShort = 0
    openorderLong = abs(float(usdt_p_l[0]["positionAmt"])) > 0
    openorderShort = abs(float(usdt_p_s[0]["positionAmt"])) > 0
    tp_long = 0
    tp_short = 0
    filled_order_long = 0

    # LONG_STOP_PRICE
    if openorderLong:
        if isinstance(order_history, list) and len(order_history) > 0:
            new_orders_long = [
                order for order in order_history if ((order.get("status") == "NEW" or order.get("status") == "CANCELED") and order.get("positionSide") == "LONG")]
            filled_orders = [
                order for order in order_history if (order.get("status") == "FILLED" and order.get("positionSide") == "LONG")]
            filled_order_long = filled_orders
            if len(filled_orders) > 0:
                if len(filled_orders) > 0 and current_milliseconds - filled_orders[-1]["time"] > (minute_limit*60*1000):
                    unRealizedProfit = float(usdt_p_l[0]["unRealizedProfit"])
                    isolatedWallet = float(usdt_p_l[0]["isolatedWallet"])
                    if isolatedWallet > 0:
                        unRealizedProfitPercentLong = unRealizedProfit * \
                            100 / isolatedWallet
            else:
                unRealizedProfit = float(usdt_p_l[0]["unRealizedProfit"])
                isolatedWallet = float(usdt_p_l[0]["isolatedWallet"])
                if isolatedWallet > 0:
                    unRealizedProfitPercentLong = unRealizedProfit * \
                        100 / isolatedWallet
        else:
            unRealizedProfit = float(usdt_p_l[0]["unRealizedProfit"])
            isolatedWallet = float(usdt_p_l[0]["isolatedWallet"])
            unRealizedProfitPercentLong = unRealizedProfit * \
                100 / isolatedWallet

    # SHORT_STOP_PRICE
    if openorderShort:
        if isinstance(order_history, list) and len(order_history) > 0:
            new_orders_short = [
                order for order in order_history if ((order.get("status") == "NEW" or order.get("status") == "CANCELED") and order.get("positionSide") == "SHORT")]
            filled_orders = [
                order for order in order_history if (order.get("status") == "FILLED" and order.get("positionSide") == "SHORT")]
            if len(filled_orders) > 0:
                if len(filled_orders) > 0 and current_milliseconds - filled_orders[-1]["time"] > (minute_limit*60*1000):
                    unRealizedProfit = float(usdt_p_s[0]["unRealizedProfit"])
                    isolatedWallet = float(usdt_p_s[0]["isolatedWallet"])
                    if isolatedWallet > 0:
                        unRealizedProfitPercentShort = unRealizedProfit * \
                            100 / isolatedWallet
            else:
                unRealizedProfit = float(usdt_p_s[0]["unRealizedProfit"])
                isolatedWallet = float(usdt_p_s[0]["isolatedWallet"])
                if isolatedWallet > 0:
                    unRealizedProfitPercentShort = unRealizedProfit * \
                        100 / isolatedWallet
        else:
            unRealizedProfit = float(usdt_p_s[0]["unRealizedProfit"])
            isolatedWallet = float(usdt_p_s[0]["isolatedWallet"])
            if isolatedWallet > 0:
                unRealizedProfitPercentShort = unRealizedProfit * \
                    100 / isolatedWallet

    tp_order(openbar, mark_price, openprice, close, max_profit_check, pmeanline, unRealizedProfitPercentLong, unRealizedProfitPercentShort, new_orders_long,
             new_orders_short, usdt_p_l, usdt_p_s, low, high, r3, s3, r1, s1, highest_long, lowest_short, client, symbol)

    return {
        'balance': usdt_b,
        'symbol': symbol,
        'short': usdt_p_s,
        'long': usdt_p_l,
        'mark_price': mark_price,
        'minqty': minqty,
        'TPL': unRealizedProfitPercentLong > max_profit_check and low <= r3,
        'TPS': unRealizedProfitPercentShort > max_profit_check and high >= s3,
        'TPP_L': tp_long,
        'TPP_S': tp_short,
        'winrate': winrate,
        'lossable': lossable,
        'win_margin': win_margin,
        'loss_margin': loss_margin,
        'unRealizedProfitOpenningShort': unRealizedProfitOpenningShort,
        'unRealizedProfitOpenningLong': unRealizedProfitOpenningLong,
        'winrate_margin': winrate_margin,
        'lossable_margin': lossable_margin
    }


def tp_order(openbar, mark_price, openprice, close, max_profit_check, pmeanline, unRealizedProfitPercentLong, unRealizedProfitPercentShort, new_orders_long, new_orders_short, usdt_p_l, usdt_p_s, low, high, r3, s3, r1, s1, highest_long, lowest_short, client: UMFutures, symbol="ETHUSDT"):
    closeprice = 0
    # LONG
    if ((unRealizedProfitPercentLong > max_profit_check and (low <= r3 and mark_price < openprice)) or
            (unRealizedProfitPercentLong > 0.1 and float(usdt_p_l[0]['entryPrice']) > r1 and (mark_price < openprice or close < openprice)) or
            (unRealizedProfitPercentLong > 0.1 and float(usdt_p_l[0]['entryPrice']) > r3 and openbar >= 8)):
        if len(new_orders_long) > 0 and new_orders_long[-1]['status'] == "NEW":
            last_stop_price = float(new_orders_long[-1]['stopPrice'])
            closeprice_by_mark = (float(usdt_p_l[0]['markPrice']) +
                                  float(usdt_p_l[0]['entryPrice']))*0.5
            closeprice_by_highest = (highest_long +
                                     float(usdt_p_l[0]['entryPrice']))*0.5
            closeprice = closeprice_by_highest if (
                closeprice_by_highest > closeprice_by_mark and mark_price > closeprice_by_highest) else closeprice_by_mark
            tp_long = closeprice
            if closeprice > last_stop_price and mark_price > closeprice:
                client.cancel_open_orders(symbol=symbol)
                client.new_order(symbol=symbol, positionSide="LONG", side="SELL", stopPrice=int(closeprice),
                                 type="STOP_MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
        elif len(new_orders_long) == 0 or new_orders_long[-1]['status'] == "CANCELED":
            closeprice_by_mark = (float(usdt_p_l[0]['markPrice']) +
                                  float(usdt_p_l[0]['entryPrice']))*0.5
            closeprice_by_highest = (highest_long +
                                     float(usdt_p_l[0]['entryPrice']))*0.5
            closeprice = closeprice_by_highest if (
                closeprice_by_highest > closeprice_by_mark and mark_price > closeprice_by_highest) else closeprice_by_mark
            tp_long = closeprice
            if mark_price > closeprice:
                client.cancel_open_orders(symbol=symbol)
                client.new_order(symbol=symbol, positionSide="LONG", side="SELL", stopPrice=int(closeprice),
                                 type="STOP_MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
    if low > r3 and unRealizedProfitPercentLong > 0.6 and not (mark_price < openprice):
        client.cancel_open_orders(symbol=symbol)

    # SAVE REVERSE LONG
    if unRealizedProfitPercentLong >= 0.15 and unRealizedProfitPercentLong < 0.6 and (len(new_orders_long) == 0 or new_orders_long[-1]['status'] == "CANCELED"):
        if high > pmeanline and float(usdt_p_l[0]['entryPrice']) < pmeanline:
            closeprice = float(usdt_p_l[0]['entryPrice']) * 1.015
            if mark_price > closeprice:
                client.cancel_open_orders(symbol=symbol)
                client.new_order(symbol=symbol, positionSide="LONG", side="SELL", stopPrice=int(closeprice),
                                 type="STOP_MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))

    # SHORT
    if ((unRealizedProfitPercentShort > max_profit_check and (high >= s3 or mark_price > openprice)) or
            (unRealizedProfitPercentShort > 0.1 and float(usdt_p_s[0]['entryPrice']) < s1 and (mark_price > openprice or close > openprice)) or
            (unRealizedProfitPercentShort > 0.1 and float(usdt_p_s[0]['entryPrice']) < s3 and openbar >= 8)):
        if len(new_orders_short) > 0 and new_orders_short[-1]['status'] == "NEW":
            last_stop_price = float(new_orders_short[-1]['stopPrice'])
            closeprice_by_mark = (float(usdt_p_s[0]['markPrice']) +
                                  float(usdt_p_s[0]['entryPrice']))*0.5
            closeprice_by_lowest = (lowest_short +
                                    float(usdt_p_s[0]['entryPrice']))*0.5
            closeprice = closeprice_by_lowest if (
                closeprice_by_lowest < closeprice_by_mark and mark_price < closeprice_by_lowest) else closeprice_by_mark
            tp_short = closeprice
            if closeprice < last_stop_price and mark_price < closeprice:
                client.cancel_open_orders(symbol=symbol)
                client.new_order(symbol=symbol, positionSide="SHORT", side="BUY", stopPrice=int(closeprice),
                                 type="STOP_MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))
        elif len(new_orders_short) == 0 or new_orders_short[-1]['status'] == "CANCELED":
            closeprice_by_mark = (float(usdt_p_s[0]['markPrice']) +
                                  float(usdt_p_s[0]['entryPrice']))*0.5
            closeprice_by_lowest = (
                lowest_short + float(usdt_p_s[0]['entryPrice']))*0.5
            closeprice = closeprice_by_lowest if (
                closeprice_by_lowest < closeprice_by_mark and mark_price < closeprice_by_lowest) else closeprice_by_mark
            tp_short = closeprice
            if mark_price < closeprice:
                client.cancel_open_orders(symbol=symbol)
                client.new_order(symbol=symbol, positionSide="SHORT", side="BUY", stopPrice=int(closeprice),
                                 type="STOP_MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))
    if high < s3 and unRealizedProfitPercentShort > 0.6 and not (mark_price > openprice):
        client.cancel_open_orders(symbol=symbol)

    # SAVE REVERSE SHORT
    if unRealizedProfitPercentShort >= 0.15 and unRealizedProfitPercentShort < 0.6 and (len(new_orders_short) == 0 or new_orders_short[-1]['status'] == "CANCELED"):
        if low < pmeanline and float(usdt_p_s[0]['entryPrice']) > pmeanline:
            closeprice = float(usdt_p_s[0]['entryPrice']) * 0.985
            if mark_price < closeprice:
                client.cancel_open_orders(symbol=symbol)
                client.new_order(symbol=symbol, positionSide="SHORT", side="BUY", stopPrice=int(closeprice),
                                 type="STOP_MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))


def lossable_calculate(client: UMFutures, symbol="ETHUSDT"):

    positions = client.get_account_trades(symbol=symbol, limit=1000)
    positions = list(filter(lambda x: float(x['realizedPnl']) != 0, positions))
    win_margin = 0
    loss_margin = 0
    wincount = 0
    losscount = 0
    winrate = 0
    lossable = 0
    winrate_margin = 0
    lossable_margin = 0

    for p in reversed(positions):
        if float(p['realizedPnl']) > 0:
            wincount += 1
            win_margin += float(p['realizedPnl'])
        elif float(p['realizedPnl']) < 0:
            losscount += 1
            loss_margin += -(float(p['realizedPnl']))

    if positions.__len__() >= 3:
        winrate = (wincount*100)/(wincount+losscount)
        lossable = (wincount*100)/(wincount+losscount+1)
        winrate_margin = (win_margin*100)/(win_margin+loss_margin)
        lossable_margin = -((win_margin/3) - loss_margin)  # 75% win-margin

    return winrate, lossable, winrate_margin, lossable_margin, win_margin, loss_margin


@app.route("/order", methods=["POST"])
def order():

    request = app.current_request
    message = request.json_body

    api_use = None
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])

    leverage = 1
    symbol = message['symbol']
    balance = client.balance()
    position_risk = client.get_position_risk(symbol=symbol)
    usdt_b = list(filter(lambda x: (x['asset'] == "USDT") if "USDT" in symbol else (x['asset'] == "BUSD"), balance))[
        0]['balance']

    usdt_p_l = list(filter(
        lambda x: x['symbol'] == symbol and x['positionSide'] == "LONG", position_risk))
    usdt_p_s = list(filter(
        lambda x: x['symbol'] == symbol and x['positionSide'] == "SHORT", position_risk))

    mark_price = 0
    if len(usdt_p_l) > 0:
        mark_price = float(message['close']) if ('close' in message and float(
            usdt_p_l[0]['markPrice']) == 0) else float(usdt_p_l[0]['markPrice'])
    elif len(usdt_p_s) > 0:
        mark_price = float(message['close']) if ('close' in message and float(
            usdt_p_s[0]['markPrice']) == 0) else float(usdt_p_s[0]['markPrice'])

    minqty = 0 if mark_price == 0 else round(
        (float(usdt_b)*0.3) / (mark_price/leverage), 3)

    opentrades = int(str(message['opentrades']))
    isOpen = True

    if minqty > 0:

        if opentrades > 0:

            positionSide = message['positionSide']
            barstatus = message['barstatus']
            # openprice = float(str(message['openprice']))
            # openbar = int(str(message['openbar']))

            if 's3' in message:

                s3 = float(str(message['s3']))
                s1 = float(str(message['s1']))
                r3 = float(str(message['r3']))
                r1 = float(str(message['r1']))

                if positionSide == "LONG":

                    if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
                        client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                         type="MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))

                    if (abs(float(usdt_p_l[0]['positionAmt'])) < opentrades*minqty) and barstatus == "UP":
                        if abs(float(usdt_p_l[0]['positionAmt'])) == 0:
                            client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                        elif (abs(float(usdt_p_l[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
                            if mark_price <= s1:
                                leftQty = minqty - \
                                    abs(float(usdt_p_l[0]['positionAmt']))
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(leftQty, 3))
                        elif (abs(float(usdt_p_l[0]['positionAmt'])) < 1.5*minqty and opentrades >= 2):
                            if mark_price <= s1:
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                        elif (abs(float(usdt_p_l[0]['positionAmt'])) < 2.5*minqty and opentrades >= 3):
                            if mark_price <= s3:
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))

                if positionSide == "SHORT":

                    if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
                        client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                         type="MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))

                    if (abs(float(usdt_p_s[0]['positionAmt'])) < opentrades*minqty) and barstatus == "DOWN":
                        if abs(float(usdt_p_s[0]['positionAmt'])) == 0:
                            client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                        elif (abs(float(usdt_p_s[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
                            if mark_price >= r1:
                                leftQty = minqty - \
                                    abs(float(usdt_p_s[0]['positionAmt']))
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(leftQty, 3))
                        elif (abs(float(usdt_p_s[0]['positionAmt'])) < 1.5*minqty and opentrades >= 2):
                            if mark_price >= r1:
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                        elif (abs(float(usdt_p_s[0]['positionAmt'])) < 2.5*minqty and opentrades >= 3):
                            if mark_price >= r3:
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))

            elif 'opp_pfiboh' in message and not ('livebar' in message):

                opp_pfiboh = int(str(message['opp_pfiboh']))
                opp_pfibol = int(str(message['opp_pfibol']))
                p_fibol = int(str(message['p_fibol']))
                p_fiboh = int(str(message['p_fiboh']))
                lp_fibol = int(str(message['lp_fibol']))
                hp_fibol = int(str(message['hp_fibol']))
                lp_fiboh = int(str(message['lp_fiboh']))
                hp_fiboh = int(str(message['hp_fiboh']))
                open = float(str(message['open']))

                if positionSide == "LONG":

                    # Close
                    if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
                        client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                         type="MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))
                    # Open
                    cc1 = p_fibol - lp_fibol >= 2 and opp_pfibol - lp_fibol >= 2
                    cc2 = lp_fiboh - p_fiboh >= 2 and lp_fiboh - opp_pfiboh >= 2
                    cc3 = p_fibol - lp_fibol >= 3 and opp_pfibol - lp_fibol >= 3
                    cc4 = lp_fiboh - p_fiboh >= 3 and lp_fiboh - opp_pfiboh >= 3
                    fcc = mark_price > open

                    if (abs(float(usdt_p_l[0]['positionAmt'])) < opentrades*minqty) and barstatus == "UP":
                        if abs(float(usdt_p_l[0]['positionAmt'])) == 0:
                            client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                        elif (abs(float(usdt_p_l[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
                            if fcc and (cc1 or cc2):
                                leftQty = minqty - \
                                    abs(float(usdt_p_l[0]['positionAmt']))
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(leftQty, 3))
                        elif (abs(float(usdt_p_l[0]['positionAmt'])) < 1.5*minqty and opentrades >= 2):
                            if fcc and (cc1 or cc2):
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                        elif (abs(float(usdt_p_l[0]['positionAmt'])) < 2.5*minqty and opentrades >= 3):
                            if fcc and (cc3 or cc4):
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))

                if positionSide == "SHORT":

                    # Close
                    if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
                        client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                         type="MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))

                    # Open
                    cc1 = hp_fibol - p_fibol >= 2 and hp_fibol - opp_pfibol >= 2
                    cc2 = p_fiboh - hp_fiboh >= 2 and opp_pfiboh - hp_fiboh >= 2
                    cc3 = hp_fibol - p_fibol >= 3 and hp_fibol - opp_pfibol >= 3
                    cc4 = p_fiboh - hp_fiboh >= 3 and opp_pfiboh - hp_fiboh >= 3
                    fcc = mark_price < open

                    if (abs(float(usdt_p_s[0]['positionAmt'])) < opentrades*minqty) and barstatus == "DOWN":
                        if abs(float(usdt_p_s[0]['positionAmt'])) == 0:
                            client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                        elif (abs(float(usdt_p_s[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
                            if fcc and (cc1 or cc2):
                                leftQty = minqty - \
                                    abs(float(usdt_p_s[0]['positionAmt']))
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(leftQty, 3))
                        elif (abs(float(usdt_p_s[0]['positionAmt'])) < 1.5*minqty and opentrades >= 2):
                            if fcc and (cc1 or cc2):
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                        elif (abs(float(usdt_p_s[0]['positionAmt'])) < 2.5*minqty and opentrades >= 3):
                            if fcc and (cc3 or cc4):
                                client.new_order(symbol=symbol, positionSide=positionSide, side=(
                                    "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))

        else:
            if abs(float(usdt_p_l[0]['positionAmt'])) > 0 and float(usdt_p_l[0]['unRealizedProfit']) > 0:
                client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                 type="MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
            if abs(float(usdt_p_s[0]['positionAmt'])) > 0 and float(usdt_p_s[0]['unRealizedProfit']) > 0:
                client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                 type="MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))

    return {'symbol': symbol, 'short': usdt_p_s[0], 'long': usdt_p_l[0], 'mark_price': mark_price, 'minqty': minqty}


@app.route("/get-outbound")
def get_outbound_ip():
    target_host = 'httpbin.org'  # You can replace this with any public endpoint
    conn = http.client.HTTPConnection(target_host)
    try:
        conn.request("GET", "/ip")
        response = conn.getresponse()
        if response.status == 200:
            data = response.read().decode('utf-8')

            # Parse the JSON response to get your Lambda's outbound IP
            ip_info = json.loads(data)
            outbound_ip = ip_info['origin']

            return outbound_ip
        else:
            return f"Failed to get IP. Response status: {response.status}"
    except Exception as e:
        return f"An error occurred: {str(e)}"
    finally:
        conn.close()
