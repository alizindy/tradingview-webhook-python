from chalice import Chalice
# from binance.client import Client
from binance.um_futures import UMFutures
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from collections import defaultdict

import time
import http.client
import json
import requests
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from datetime import datetime, timedelta

app = Chalice(app_name='tradingview-webhook')

cred = credentials.Certificate(
    'bottrade-dashboard-firebase-adminsdk-by3tf-2044eebed0.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://bottrade-dashboard-default-rtdb.asia-southeast1.firebasedatabase.app"
})
ref_key = db.reference('keysecret')
ref_user = db.reference("users")
ref_history = db.reference('history_trade_mark')
ref_apistatus = db.reference('api_status')
# data = [
#     {"key": 'uiTblJmq60Hjege6KTXLw9ANMdOnWSPxIp8I56Gp6FORHvk5M768DxP31yTLlxSj',
#         "secret": "bWqeK7VLxsaXf2gBF5dA6EynVX7A825vYmwoMdY2rUyTmnytuJV4xbTspcAdpkax"},
#     {"key": 'bVXg4acFCMdpqbXZNhoLQyw3VgqNekfKLlEzZk9NGrmWvXd6iWyS9kQjyPQIOnxB',
#         "secret": "w5xL8MSwYnsNgkLNlxUw6bpJIPC1MWxak7NPLsDz6WK8nuQ0QgPNyREyrq2ShQqD"},
#     {"key": 'jtvE5jrzTIIjcJu6M9t2ic72pTOci745md4G31h92q6DFG5Osmd4sLTmDbNtGKBI',
#         "secret": "4Vq1tS8wmv8yDfar7z7gQp7UmEU8kKus9GCVmmWXFzGiXifHlTEXcnHpozkZ5elT"},
#     {"key": 'NdkAXr3jEiUdaA6uUmy19mhUBeexiTqtEWVwTpNTW3NWiQM3AxutUbo2dYGi9OM7',
#      "secret": 'VgW5tyci24xUwVJU5odxsj4leUiREDKzbDCXJEbhROFEoomQO2wLHdJTrgPiyfSW'},
#     {"key": 'Hx5SpLDeEU3UHpgrGjMQvTbkxeFuDfeQjmpKkEf3bO1ubaIqJA6bf7uHi3l7iR3u',
#      "secret": 'lnlh15QHULHaDzFTHDlD0RJEBiPjH1xrbLX4UiYZsk3vBsW12MwrqbtgXsQzsJJP'},
# ]


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


@app.route('/bot-dashboard', methods=['POST', 'OPTION'], cors=True)
def check_history_position():

    request = app.current_request
    message = request.json_body
    symbol = "ETHUSDT"

    # start_time_str = message.get('start_time')
    # end_time_str = message.get('end_time')

    # if start_time_str is not None:
    #     start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    #     end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    #     startTime = int(start_time.timestamp() * 1000)
    #     endTime = int(end_time.timestamp() * 1000)
    # else:
    #     start_time = None
    #     end_time = None

    api_use = None
    data = ref_key.get()
    data = list(filter(lambda x: x != None, data))
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])

    balance = client.balance()
    position_risk = client.get_position_risk(symbol="ETHUSDT")
    position_history = None

    return {"balance": balance, "position": position_risk}


@app.route('/check-history-position-all', methods=['POST', 'OPTION'], cors=True)
def check_history_position_all():

    url = 'https://fapi.binance.com/fapi/v1/time'
    response = requests.get(url)
    servertime_ms = 0
    if response.status_code == 200:
        data_time = response.json()
        servertime_ms = data_time['serverTime']

    requestData = app.current_request
    message = requestData.json_body
    symbol = "ETHUSDT"

    api_use = None
    data = ref_key.get()
    data = list(filter(lambda x: x != None, data))
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])

    startTime = 1704189600000
    endTime = servertime_ms
    slice_duration_seconds = 7 * 24 * 60 * 60
    merged_trades = []

    while startTime < endTime:
        slice_end_time = min(
            startTime + slice_duration_seconds * 1000, endTime)
        history_trades = client.get_account_trades(
            symbol=symbol, limit=1000, startTime=startTime, endTime=slice_end_time)
        merged_trades.extend(history_trades)
        startTime = slice_end_time
        time.sleep(0.1)

    close_shorts = list(
        filter(lambda x: x['positionSide'] == 'SHORT' and x['side'] == 'BUY', merged_trades))
    lastclose_short = close_shorts[-1] if close_shorts.__len__() > 0 else {}
    close_longs = list(
        filter(lambda x: x['positionSide'] == 'LONG' and x['side'] == 'SELL', merged_trades))
    lastclose_long = close_longs[-1] if close_longs.__len__() > 0 else {}

    return {'history': merged_trades, 'lastshort': lastclose_short, 'lastlong': lastclose_long}


@app.route('/check-history-position', methods=['POST', 'OPTION'], cors=True)
def check_history_position():
    request = app.current_request
    message = request.json_body
    symbol = "ETHUSDT"

    url = 'https://fapi.binance.com/fapi/v1/time'
    response = requests.get(url)
    servertime_ms = 0
    if response.status_code == 200:
        data_time = response.json()
        servertime_ms = data_time['serverTime']

    start_time_str = message.get('start_time')
    end_time_str = message.get('end_time')

    if start_time_str is not None:
        start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        # start_time += timedelta(hours=7)
        # end_time += timedelta(hours=7)
        startTime = int(start_time.timestamp() * 1000)
        endTime = int(end_time.timestamp() * 1000)
    else:
        start_time = None
        end_time = None

    endTime = servertime_ms if endTime > servertime_ms and servertime_ms != 0 else endTime

    api_use = None
    data = ref_key.get()
    data = list(filter(lambda x: x != None, data))
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])
    history_trades = None

    if start_time_str is not None:
        history_trades = client.get_account_trades(
            symbol=symbol, startTime=startTime, endTime=endTime)
    else:
        history_trades = client.get_account_trades(symbol=symbol, limit=1000)

    close_shorts = list(
        filter(lambda x: x['positionSide'] == 'SHORT' and x['side'] == 'BUY', history_trades))
    lastclose_short = close_shorts[-1] if close_shorts.__len__() > 0 else {}
    close_longs = list(
        filter(lambda x: x['positionSide'] == 'LONG' and x['side'] == 'SELL', history_trades))
    lastclose_long = close_longs[-1] if close_longs.__len__() > 0 else {}

    return {'history': history_trades, 'lastshort': lastclose_short, 'lastlong': lastclose_long}


@app.route('/testing_place_stopprice', methods=["POST"])
def testing_place_stopprice():

    request = app.current_request
    message = request.json_body
    symbol = "ETHUSDT"

    api_use = None
    data = ref_key.get()
    data = list(filter(lambda x: x != None, data))
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
    data = ref_key.get()
    data = list(filter(lambda x: x != None, data))
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

    leverage = 1
    if len(usdt_p_l) > 0:
        minqty = 0 if float(usdt_p_l[0]['markPrice']) == 0 else round(
            (float(usdt_b)*0.3) / (float(usdt_p_l[0]['markPrice'])/leverage), 3)
    else:
        minqty = 0

    position_history = client.get_position_margin_history(
        symbol="ETHUSDT")
    timefulls = [item['time'] for item in position_history]
    timeeach = list(
        map(lambda x: (datetime.utcfromtimestamp(x/1000)).strftime('%Y-%m-%d %H:%M'), timefulls))

    return {
        'balance': float(usdt_b),
        'position_long': usdt_p_l,
        'position_short': usdt_p_s,
        'position_time': timefulls,
        'position_history': str(timeeach),
        'minqty': minqty
    }


@app.route("/get-first-position", methods=["POST"])
def get_first_position():
    request = app.current_request
    message = request.json_body

    api_use = None
    data = ref_key.get()
    data = list(filter(lambda x: x != None, data))
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])
    symbol = 'ETHUSDT'
    return client.get_account_trades(symbol=symbol, limit=1000, startTime=1707300000005, endTime=1707904800000)


@app.route("/change-position-mode", methods=["POST"])
def change_position_mode():
    request = app.current_request
    message = request.json_body

    api_use = None
    data = ref_key.get()
    data = list(filter(lambda x: x != None, data))
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])
    client.change_margin_type(marginType="ISOLATED", symbol="ETHUSDT")


@app.route("/order-MRMFRS", methods=["POST"])
# Mean Reversal + MACD + Fibonacci + Resistance and Support
def order_mrmfrs():

    request = app.current_request
    message = request.json_body

    api_use = None
    data = ref_key.get()
    data = list(filter(lambda x: x != None, data))
    # for obj in data:
    #     if 'key' in obj and obj['key'] == message['key']:
    #         api_use = obj
    #         break

    condition_o1 = None
    condition_o2 = None
    condition_o3 = None
    condition_o4 = None
    condition_o5 = None
    condition_o11 = None
    condition_o12 = None
    positionSide = ""
    opentime = None

    balances = []
    for key_active in data:
        if key_active["active"] == True:

            api_use = key_active
            client = UMFutures(api_use['key'], api_use['secret'])

            leverage = 1
            symbol = message['symbol']
            balance = client.balance()
            position_risk = client.get_position_risk(symbol=symbol)
            usdt_b_all = list(filter(lambda x: (x['asset'] == "USDT") if "USDT" in symbol else (x['asset'] == "BUSD"), balance))[
                0]['balance']
            usdt_b = 20000 if float(usdt_b_all) > 20000 else float(usdt_b_all)
            balances.append(float(usdt_b_all))

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
            rsiMAConState = message['rsiMAConState']
            pmeanlineState = message['pmeanlineState']
            rsiCrossState = message['rsiCrossState']

            highest = float(message['highest'])
            lowest = float(message['lowest'])
            high = float(message['high'])
            low = float(message['low'])
            close = float(message['close'])
            open = 0 if message['open'] == "NaN" else float(message['open'])
            openbar = 0 if message['openbar'] == "NaN" else int(
                message['openbar'])
            openprice = 0 if message['openprice'] == "NaN" else float(
                message['openprice'])

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
            pmeanline_trendline = float(message['pmeanline_trendline'])
            highest_long = float(message['highest_long'])
            lowest_short = float(message['lowest_short'])
            last_sp = []
            last_lp = []
            minqtyclose_safe = 0

            positions_history = client.get_account_trades(
                symbol=symbol, limit=1000)
            lastclose_shorts = list(
                filter(lambda x: x['positionSide'] == 'SHORT' and x['side'] == 'BUY', positions_history))
            lastclose_longs = list(
                filter(lambda x: x['positionSide'] == 'LONG' and x['side'] == 'SELL', positions_history))
            lastclose_short = lastclose_shorts[-1] if lastclose_shorts.__len__(
            ) > 0 else None
            lastclose_long = lastclose_longs[-1] if lastclose_longs.__len__(
            ) > 0 else None

            winrate, lossable, winrate_margin, lossable_margin, win_margin, loss_margin = lossable_calculate(
                positions_history, symbol)

            curr_openning_cumprofit = get_current_openning_cumprofit(
                client=client, symbol=symbol)

            if minqty > 0:

                if opentrades > 0:

                    positionSide = message['positionSide']
                    barstatus = message['barstatus']
                    opentime = message['opentime']

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

                        # Close By Calculate on Same opentime openning
                        if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
                            if (((curr_openning_cumprofit['sum_pos_short']+curr_openning_cumprofit['sum_neg_short'])*100) / float(usdt_p_s[0]['isolatedWallet'])) >= 0.6:
                                if (float(usdt_p_s[0]['unRealizedProfit']) < 0 and
                                    abs(float(usdt_p_s[0]['unRealizedProfit'])+curr_openning_cumprofit['sum_neg_short']) >= (0.5*curr_openning_cumprofit['sum_pos_short']) and
                                        abs(float(usdt_p_s[0]['unRealizedProfit'])+curr_openning_cumprofit['sum_neg_short']) <= (0.75*curr_openning_cumprofit['sum_pos_short'])):
                                    shortclose_remark = "BELOW_HALF_PROFIT"
                                    write_to_history({"positionSide": "SHORT", "side": "BUY", "remark": shortclose_remark,
                                                      "key": api_use['key'], "profitPercent": unRealizedProfitPercentOpenningShort, "profit": unRealizedProfitOpenningShort})
                                    client.cancel_open_orders(symbol=symbol)
                                    client.new_order(symbol=symbol, positionSide="SHORT", side="BUY", type="MARKET", quantity=round(
                                        abs(float(usdt_p_s[0]['positionAmt'])), 3))
                        if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
                            if (((curr_openning_cumprofit['sum_pos_long']+curr_openning_cumprofit['sum_neg_long'])*100) / float(usdt_p_l[0]['isolatedWallet'])) >= 0.6:
                                if (float(usdt_p_l[0]['unRealizedProfit']) < 0 and
                                    abs(float(usdt_p_l[0]['unRealizedProfit'])+curr_openning_cumprofit['sum_neg_long']) >= (0.5*curr_openning_cumprofit['sum_pos_long']) and
                                        abs(float(usdt_p_l[0]['unRealizedProfit'])+curr_openning_cumprofit['sum_neg_long']) <= (0.75*curr_openning_cumprofit['sum_pos_long'])):
                                    longclose_remark = "BELOW_HALF_PROFIT"
                                    write_to_history({"positionSide": "LONG", "side": "SELL", "remark": longclose_remark,
                                                      "key": api_use['key'], "profitPercent": unRealizedProfitPercentOpenningLong, "profit": unRealizedProfitOpenningLong})
                                    client.cancel_open_orders(symbol=symbol)
                                    client.new_order(symbol=symbol, positionSide="LONG", side="SELL", type="MARKET", quantity=round(
                                        abs(float(usdt_p_l[0]['positionAmt'])), 3))
                        # Close By Calculate on Same opentime openning

                        if positionSide == "LONG":

                            # Opposite Open Safe
                            if abs(float(usdt_p_l[0]['positionAmt'])) > minqty*1.5 and abs(float(usdt_p_l[0]['positionAmt'])) < minqty*2.5 and abs(float(usdt_p_s[0]['positionAmt'])) == 0:
                                if unRealizedProfitPercentOpenningLong < -1.2:
                                    if rsiMAState == "DOWN" and pmeanlineState == "DOWN" and pmeanline > sp and (r1 > openprice or float(message['rsiMA15'] > 50)):
                                        write_to_history(
                                            {"positionSide": "SHORT", "side": "SELL", "remark": "OPPOSITE_OPEN_SAFE", "key": api_use['key'], "opentime": int(opentime)})
                                        client.new_order(
                                            symbol=symbol, positionSide="SHORT", side="SELL", type="MARKET", quantity=round(minqty, 3))

                            # Wrong Side Fixing Position
                            # if winrate >= 70 and abs(float(usdt_p_s[0]['positionAmt'])) > 0 and unRealizedProfitPercentOpenningShort < -1.2 and s3 - abs(float(usdt_p_s[0]['entryPrice'])) > r1 - s3:
                            #     lossable_ratio = (
                            #         abs(float(usdt_p_s[0]['entryPrice'])) - mark_price) / lossable_margin
                            #     minqtyclose_safe = round(
                            #         abs(float(usdt_p_s[0]['positionAmt'])) / lossable_ratio, 3)
                            #     if lossable_ratio > 0 and minqtyclose_safe > 0.010:
                            #         if (float(message['rsi15']) <= 30 and float(message['rsiMA15']) < 50) or float(message['rsiMA15']) <= 30 or (float(message['rsiMA']) > 70 and float(message['rsi']) < 70 and rsiMAConState == "UP") or mark_price < s3:
                            #             write_to_history(
                            #                 {"positionSide": "SHORT", "side": "BUY", "remark": "WRONGSIDE_FIXING_POSITION", "key": api_use['key']})
                            #             client.new_order(
                            #                 symbol=symbol, positionSide="SHORT", side="BUY", type="MARKET", quantity=minqtyclose_safe)

                            # Close Short on Open Long
                            quantityclose = 0
                            shortclose_remark = ""
                            if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
                                # Close By Normal Condition
                                if openbar >= 1 or float(usdt_p_s[0]['unRealizedProfit']) > 0:
                                    if unRealizedProfitPercentOpenningShort > 0.3:
                                        quantityclose = abs(float(
                                            usdt_p_s[0]['positionAmt'])) if (unRealizedProfitPercentOpenningShort <= 0.6 or abs(float(
                                                usdt_p_s[0]['positionAmt'])) < minqty) else round(minqty, 3)
                                        shortclose_remark = "PROFITABLE"
                                    else:
                                        if (float(usdt_p_s[0]['entryPrice']) - mark_price)*minqty > lossable_margin and lossable >= 75 and float(message['rsi']) > 30 and float(message['rsiMA']) > 30 and ((barstatus == "UP" and mark_price > open) or (rsiCrossState == "UP") or low >= r1 or high <= s1 or float(usdt_p_s[0]['entryPrice']) <= s3):
                                            if ((rsiMAState == "UP" and float(message['rsi']) > float(message['rsiMA']) and mark_price > open) or
                                                (barstatus == "UP" and mark_price > open) or
                                                    (float(message['rsi15']) <= 30 or float(message['rsiMA15']) <= 30) or
                                                    (rsiCrossState == "UP")):
                                                quantityclose = abs(float(usdt_p_s[0]['positionAmt'])) if abs(float(
                                                    usdt_p_s[0]['positionAmt'])) < minqty*1.5 else minqty
                                                shortclose_remark = "LOSSABLE_CONTROL"
                                        else:
                                            if abs(float(usdt_p_s[0]['positionAmt'])) <= minqty*1.5:
                                                if (unRealizedProfitPercentOpenningLong > abs(unRealizedProfitPercentOpenningShort)*2 and unRealizedProfitPercentOpenningLong > 1.2):
                                                    if (not (float(message['rsiMA15']) >= 70 or (float(message['rsiMA15']) >= 65 and float(message['rsi15']) >= 70))) and (not (rsiMAState == "UP" and pmeanlineState == "UP")):
                                                        quantityclose = abs(
                                                            float(usdt_p_s[0]['positionAmt']))
                                                        shortclose_remark = "DOUBLEPROFIT_ON_LONGSIDE"
                                            # else:
                                            #     if opentrades == 3:
                                            #         if s3 > pmop or r3 < pmop or float(message['rsi']) <= 30 or (opentrades > 2 and (float(message['rsi']) <= 50 or mark_price < pmeanline)) or (pass_s3 and mark_price < s1) or float(message['rsiMA']) <= 30 or unRealizedProfitPercentOpenningLong >= 1.2:
                                            #             if abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*1.5:
                                            #                 quantityclose = minqty
                                            #                 shortclose_remark = "LONG_OPEN_3"
                                            #     if opentrades == 2:
                                            #         if abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*2.5:
                                            #             quantityclose = minqty
                                            #             shortclose_remark = "LONG_OPEN_2"

                                    if quantityclose > 0:
                                        client.cancel_open_orders(
                                            symbol=symbol)
                                        write_to_history(
                                            {"positionSide": "SHORT", "side": "BUY", "remark": "NORMAL_"+shortclose_remark, "key": api_use['key'], "profitPercent": unRealizedProfitPercentOpenningShort, "profit": unRealizedProfitOpenningShort})
                                        client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                                         type="MARKET", quantity=round(quantityclose, 3))

                            # Open
                            condition_o1 = (1 if (openbar >= 1) else
                                            (2 if abs(float(usdt_p_s[0]['positionAmt'])) == 0 else
                                            (3 if float(usdt_p_s[0]['unRealizedProfit']) > 0 else
                                             (4 if abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*1.5 else None))))

                            condition_o2 = (1 if lastclose_long == None else
                                            (2 if float(lastclose_long['realizedPnl']) > 0 else
                                             (3 if (curr_openning_cumprofit['last_openning_long'] == None) else
                                             (4 if (openbar < 4 and curr_openning_cumprofit['last_openning_long'] != None and curr_openning_cumprofit['last_openning_long']['opentime'] != opentime) else
                                              (5 if (rsiMAState == "UP" and pmeanlineState == "UP" and barstatus == "UP" and mark_price < (r1+pmeanline)*0.5) else
                                              (6 if (r1 < sp and mark_price < s1 and barstatus != "DOWN") else None))))))

                            condition_o3 = (1 if openbar < 8 else
                                            (2 if (rsiCrossState == "UP") else
                                             (3 if (barstatus == "UP" and mark_price > open) else
                                             (4 if (s1 < openprice) else
                                              (5 if (mark_price < s1) else
                                              (6 if (float(message['rsi15']) <= 30) else
                                               (7 if (float(message['rsi15']) < float(message['rsiMA15'] and float(message['rsiMA15']) < 50)) else None)))))))

                            condition_o4 = (1 if openbar < 8 else
                                            (2 if (rsiCrossState == "UP" and high != highest) else
                                             (3 if (rsiMAState == "UP" and float(message['rsi']) > float(message['rsiMA']) and mark_price > open) else
                                             (4 if (barstatus == "UP" and mark_price < r1 and mark_price > open) else
                                              (5 if (abs(float(usdt_p_l[0]['positionAmt'])) == 0 and (float(message['rsi']) <= 30 or float(message['rsiMA15']) <= 30)) else None)))))

                            condition_o5 = (1 if (curr_openning_cumprofit['sum_pos_long'] == 0) else
                                            (2 if (curr_openning_cumprofit['sum_neg_long'] == 0) else
                                            (3 if (curr_openning_cumprofit['last_openning_long'] == None) else
                                             (4 if (curr_openning_cumprofit['last_openning_long'] != None and curr_openning_cumprofit['last_openning_long']['opentime'] != opentime) else
                                             (5 if (abs(curr_openning_cumprofit['sum_neg_long']) < curr_openning_cumprofit['sum_pos_long']*0.5) else
                                              (6 if ((((curr_openning_cumprofit['sum_pos_long']+curr_openning_cumprofit['sum_neg_long'])*100) / float(usdt_p_l[0]['isolatedWallet'])) >= 1.2) else None))))))

                            if (condition_o1 != None):  # 4
                                if (condition_o2 != None):
                                    if (abs(float(usdt_p_l[0]['positionAmt'])) < opentrades*minqty):
                                        if ((openbar < 8) or
                                                ((condition_o3 != None) and (condition_o4 != None))):
                                            if abs(float(usdt_p_l[0]['positionAmt'])) == 0 or (abs(float(usdt_p_l[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
                                                if (condition_o5 != None):
                                                    if abs(float(usdt_p_l[0]['positionAmt'])) == 0:
                                                        write_to_history(
                                                            {"positionSide": "LONG", "side": "BUY", "remark": "0", "key": api_use['key'], "opentime": int(opentime),
                                                             "condition": str(condition_o1)+"_"+str(condition_o2)+"_"+str(condition_o3)+"_"+str(condition_o4)+"_"+str(condition_o5)})
                                                        client.cancel_open_orders(
                                                            symbol=symbol)
                                                        client.new_order(
                                                            symbol=symbol, positionSide="LONG", side="BUY", type="MARKET", quantity=round(minqty, 3))
                                                    elif (abs(float(usdt_p_l[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
                                                        leftQty = minqty - \
                                                            abs(float(
                                                                usdt_p_l[0]['positionAmt']))
                                                        write_to_history(
                                                            {"positionSide": "LONG", "side": "BUY", "remark": "LEFT", "key": api_use['key'], "opentime": int(opentime),
                                                             "condition": str(condition_o1)+"_"+str(condition_o2)+"_"+str(condition_o3)+"_"+str(condition_o4)+"_"+str(condition_o5)})
                                                        client.cancel_open_orders(
                                                            symbol=symbol)
                                                        client.new_order(
                                                            symbol=symbol, positionSide="LONG", side="BUY", type="MARKET", quantity=round(leftQty, 3))
                                            elif abs(float(usdt_p_l[0]['positionAmt'])) < 1.5*minqty and abs(float(usdt_p_s[0]['positionAmt'])) < 2*minqty:

                                                condition_o11 = (1 if (opentrades >= 2 and unRealizedProfitPercentOpenningLong >= 1.2) else
                                                                 (2 if (r3 < sp and r3 < mark_price and (curr_openning_cumprofit['last_openning_long'] == None or curr_openning_cumprofit['last_openning_long']['opentime'] != opentime)) else None))

                                                if (condition_o11 != None):

                                                    condition_o12 = (1 if (s3 > pmop and s3 > mark_price and barstatus == "UP" and (rsiMAState == "UP" or pmeanlineState == "UP")) else
                                                                     (2 if (r3 < pmop and r3 < mark_price and barstatus == "UP" and (rsiMAState == "UP" or pmeanlineState == "UP")) else
                                                                      (3 if ((s3 > mark_price or r3 < mark_price) and pmeanlineState == "UP" and rsiCrossState == "UP") else
                                                                       (4 if (pass_s3 and mark_price < s1) else
                                                                        (5 if (float(message['rsi']) <= 30) else
                                                                         (6 if (float(message['rsiMA']) <= 30) else
                                                                          (7 if (r3 < pmeanline_trendline and r3 < sp and low < s1) else
                                                                           (8 if (unRealizedProfitPercentOpenningLong >= 1.8) else None))))))))

                                                    if (condition_o12 != None):
                                                        write_to_history(
                                                            {"positionSide": "LONG", "side": "BUY", "remark": "2", "key": api_use['key'], "opentime": int(opentime),
                                                             "condition": str(condition_o11)+"_"+str(condition_o12)})
                                                        client.new_order(
                                                            symbol=symbol, positionSide="LONG", side="BUY", type="MARKET", quantity=round(minqty, 3))

                                            elif (abs(float(usdt_p_l[0]['positionAmt'])) < 2.5*minqty and abs(float(usdt_p_s[0]['positionAmt'])) < 2.9*minqty and opentrades >= 3):
                                                if ((s3 > r3op and s3 > mark_price) or
                                                    (r3 < s3op and r3 < mark_price) or
                                                        (unRealizedProfitPercentOpenningLong >= 2.6)):
                                                    write_to_history(
                                                        {"positionSide": "LONG", "side": "BUY", "remark": "3", "key": api_use['key'], "opentime": int(opentime)})
                                                    client.new_order(
                                                        symbol=symbol, positionSide="LONG", side="BUY", type="MARKET", quantity=round(minqty, 3))

                        if positionSide == "SHORT":

                            # Opposite Open Safe
                            if abs(float(usdt_p_s[0]['positionAmt'])) > minqty*1.5 and abs(float(usdt_p_s[0]['positionAmt'])) < minqty*2.5 and abs(float(usdt_p_l[0]['positionAmt'])) == 0:
                                if unRealizedProfitPercentOpenningShort < -1.2:
                                    if rsiMAState == "UP" and pmeanlineState == "UP" and pmeanline < rt and (s1 < openprice or float(message['rsiMA15']) < 50):
                                        write_to_history(
                                            {"positionSide": "LONG", "side": "BUY", "remark": "OPPOSITE_OPEN_SAFE", "key": api_use['key'], "opentime": int(opentime)})
                                        client.new_order(
                                            symbol=symbol, positionSide="LONG", side="BUY", type="MARKET", quantity=round(minqty, 3))

                            # Wrong Side Fixing Position
                            # if winrate >= 70 and abs(float(usdt_p_l[0]['positionAmt'])) > 0 and unRealizedProfitPercentOpenningLong < -1.2 and abs(float(usdt_p_l[0]['entryPrice'])) - r3 > r3 - s1:
                            #     lossable_ratio = (
                            #         mark_price - abs(float(usdt_p_l[0]['entryPrice']))) / lossable_margin
                            #     minqtyclose_safe = round(
                            #         abs(float(usdt_p_l[0]['positionAmt'])) / lossable_ratio, 3)
                            #     if lossable_ratio > 0 and minqtyclose_safe > 0.010:
                            #         if (float(message['rsi15']) >= 70 and float(message['rsiMA15']) > 50) or float(message['rsiMA15']) >= 70 or (float(message['rsiMA']) < 30 and float(message['rsi']) > 30 and rsiMAConState == "DOWN") or mark_price > r3:
                            #             write_to_history(
                            #                 {"positionSide": "LONG", "side": "SELL", "remark": "WRONGSIDE_FIXING_POSITION"})
                            #             client.new_order(
                            #                 symbol=symbol, positionSide="LONG", side="SELL", type="MARKET", quantity=minqtyclose_safe)

                            # Close Long on Short Open
                            quantityclose = 0
                            longclose_remark = ""
                            if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
                                # Close By Normal Condition
                                if openbar >= 1 or float(usdt_p_l[0]['unRealizedProfit']) > 0:
                                    if unRealizedProfitPercentOpenningLong > 0.3:
                                        quantityclose = abs(float(
                                            usdt_p_l[0]['positionAmt'])) if (unRealizedProfitPercentOpenningLong <= 0.6 or abs(float(
                                                usdt_p_l[0]['positionAmt'])) < minqty) else round(minqty, 3)
                                        longclose_remark = "PROFITABLE"
                                    else:
                                        if (mark_price - float(usdt_p_l[0]['entryPrice']))*minqty > lossable_margin and lossable >= 75 and float(message['rsi']) < 70 and float(message['rsiMA']) < 70 and ((barstatus == "DOWN" and mark_price < open) or (rsiCrossState == "DOWN") or low >= r1 or high <= s1 or float(usdt_p_l[0]['entryPrice']) >= r3):
                                            if ((rsiMAState == "DOWN" and float(message['rsi']) < float(message['rsiMA']) and mark_price < open) or
                                                (barstatus == "DOWN" and mark_price < open) or
                                                    (float(message['rsiMA15']) >= 70 and float(message['rsi15']) >= 70) or
                                                    (rsiCrossState == "DOWN")):
                                                quantityclose = abs(float(usdt_p_l[0]['positionAmt'])) if abs(float(
                                                    usdt_p_l[0]['positionAmt'])) < minqty*1.5 else minqty
                                                longclose_remark = "LOSSABLE_CONTROL"
                                        else:
                                            if abs(float(usdt_p_l[0]['positionAmt'])) <= minqty*1.5:
                                                if (unRealizedProfitPercentOpenningShort > abs(unRealizedProfitPercentOpenningLong)*2 and unRealizedProfitPercentOpenningShort > 1.2):
                                                    if not (float(message['rsiMA15']) <= 30 or (float(message['rsiMA15']) <= 35 and float(message['rsi15']) <= 30)):
                                                        quantityclose = abs(
                                                            float(usdt_p_l[0]['positionAmt']))
                                                        longclose_remark = "DOUBLEPROFIT_ON_SHORTSIDE"
                                            # else:
                                            #     if opentrades == 3:
                                            #         if s3 > pmop or r3 < pmop or float(message['rsi']) >= 70 or (opentrades > 2 and (float(message['rsi']) >= 50 or mark_price > pmeanline)) or (pass_r3 and mark_price > r1) or float(message['rsiMA']) >= 70 or unRealizedProfitPercentOpenningShort >= 1.2:
                                            #             if abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*1.5:
                                            #                 quantityclose = minqty
                                            #                 longclose_remark = "SHORT_OPEN_2"
                                            #     if opentrades == 2:
                                            #         if abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*2.5:
                                            #             quantityclose = minqty
                                            #             longclose_remark = "SHORT_OPEN_3"

                                    if quantityclose > 0:
                                        write_to_history(
                                            {"positionSide": "LONG", "side": "SELL", "remark": "NORMAL_"+longclose_remark, "key": api_use['key'], "profitPercent": unRealizedProfitPercentOpenningLong, "profit": unRealizedProfitOpenningLong})
                                        client.cancel_open_orders(
                                            symbol=symbol)
                                        client.new_order(
                                            symbol=symbol, positionSide="LONG", side="SELL", type="MARKET", quantity=round(quantityclose, 3))

                            # Open
                            condition_o1 = (1 if (openbar >= 1) else
                                            (2 if abs(float(usdt_p_l[0]['positionAmt'])) == 0 else
                                            (3 if float(usdt_p_l[0]['unRealizedProfit']) > 0 else
                                             (4 if abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*1.5 else None))))

                            condition_o2 = (1 if lastclose_short == None else
                                            (2 if float(lastclose_short['realizedPnl']) > 0 else
                                             (3 if (curr_openning_cumprofit['last_openning_short'] == None) else
                                             (4 if (openbar < 4 and curr_openning_cumprofit['last_openning_short'] != None and curr_openning_cumprofit['last_openning_short']['opentime'] != opentime) else
                                              (5 if (rsiMAState == "DOWN" and pmeanlineState == "DOWN" and barstatus == "DOWN" and mark_price > (s1+pmeanline)*0.5) else
                                              (6 if (s1 > rt and mark_price > r1 and barstatus != "UP") else None))))))

                            condition_o3 = (1 if openbar < 8 else
                                            (2 if (rsiCrossState == "UP") else
                                             (3 if (barstatus == "UP" and mark_price > open) else
                                             (4 if (s1 < openprice) else
                                              (5 if (mark_price < s1) else
                                              (6 if (float(message['rsi15']) <= 30) else
                                               (7 if (float(message['rsi15']) < float(message['rsiMA15'] and float(message['rsiMA15']) < 50)) else None)))))))

                            condition_o4 = (1 if openbar < 8 else
                                            (2 if (rsiCrossState == "DOWN" and low != lowest) else
                                             (3 if (rsiMAState == "DOWN" and float(message['rsi']) < float(message['rsiMA']) and mark_price < open) else
                                             (4 if (barstatus == "DOWN" and mark_price > s1 and mark_price < open) else
                                              (5 if (abs(float(usdt_p_s[0]['positionAmt'])) == 0 and (float(message['rsi']) >= 70 or float(message['rsiMA15']) >= 70)) else None)))))

                            condition_o5 = (1 if (curr_openning_cumprofit['sum_pos_short'] == 0) else
                                            (2 if (curr_openning_cumprofit['sum_neg_short'] == 0) else
                                            (3 if (curr_openning_cumprofit['last_openning_short'] == None) else
                                             (4 if (curr_openning_cumprofit['last_openning_short'] != None and curr_openning_cumprofit['last_openning_short']['opentime'] != opentime) else
                                             (5 if (abs(curr_openning_cumprofit['sum_neg_short']) < curr_openning_cumprofit['sum_pos_short']*0.5) else
                                              (6 if ((((curr_openning_cumprofit['sum_pos_short']+curr_openning_cumprofit['sum_neg_short'])*100) / float(usdt_p_s[0]['isolatedWallet'])) >= 1.2) else None))))))

                            if (condition_o1 != None):
                                if (condition_o2 != None):
                                    if (abs(float(usdt_p_s[0]['positionAmt'])) < opentrades*minqty):
                                        if (condition_o3 != None and condition_o4 != None):
                                            if abs(float(usdt_p_s[0]['positionAmt'])) == 0 or (abs(float(usdt_p_s[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
                                                if (condition_o5 != None):
                                                    if abs(float(usdt_p_s[0]['positionAmt'])) == 0:
                                                        client.cancel_open_orders(
                                                            symbol=symbol)
                                                        client.new_order(
                                                            symbol=symbol, positionSide="SHORT", side="SELL", type="MARKET", quantity=round(minqty, 3))
                                                        write_to_history(
                                                            {"positionSide": "SHORT", "side": "SELL", "remark": "0", "key": api_use['key'], "opentime": int(opentime),
                                                             "condition": str(condition_o1)+"_"+str(condition_o2)+"_"+str(condition_o3)+"_"+str(condition_o4)+"_"+str(condition_o5)})
                                                    elif (abs(float(usdt_p_s[0]['positionAmt'])) < 0.5*minqty and opentrades >= 1):
                                                        leftQty = minqty - \
                                                            abs(float(
                                                                usdt_p_s[0]['positionAmt']))
                                                        client.cancel_open_orders(
                                                            symbol=symbol)
                                                        client.new_order(
                                                            symbol=symbol, positionSide="SHORT", side="SELL", type="MARKET", quantity=round(leftQty, 3))
                                                        write_to_history(
                                                            {"positionSide": "SHORT", "side": "SELL", "remark": "LEFT", "key": api_use['key'], "opentime": int(opentime),
                                                             "condition": str(condition_o1)+"_"+str(condition_o2)+"_"+str(condition_o3)+"_"+str(condition_o4)+"_"+str(condition_o5)})
                                            elif abs(float(usdt_p_s[0]['positionAmt'])) < 1.5*minqty and abs(float(usdt_p_l[0]['positionAmt'])) < 1.5*minqty:

                                                condition_o11 = (1 if (opentrades >= 2 and unRealizedProfitPercentOpenningShort >= 1.2) else
                                                                 (2 if (s3 > rt and s3 > mark_price and (curr_openning_cumprofit['last_openning_short'] == None or curr_openning_cumprofit['last_openning_short']['opentime'] != opentime)) else None))

                                                if (condition_o11 != None):

                                                    condition_o12 = (1 if (s3 > pmop and s3 > mark_price and barstatus == "DOWN" and (rsiMAState == "DOWN" or pmeanlineState == "DOWN")) else
                                                                     (2 if (r3 < pmop and r3 < mark_price and barstatus == "DOWN" and (rsiMAState == "DOWN" or pmeanlineState == "DOWN")) else
                                                                      (3 if ((s3 > mark_price or r3 < mark_price) and pmeanlineState == "DOWN" and rsiCrossState == "DOWN") else
                                                                       (4 if (pass_r3 and mark_price > r1) else
                                                                        (5 if (float(message['rsi']) >= 70) else
                                                                         (6 if (float(message['rsiMA']) >= 70) else
                                                                          (7 if (s3 > pmeanline_trendline and s3 > rt and high > r1) else
                                                                           (8 if (unRealizedProfitPercentOpenningShort >= 1.8) else None))))))))

                                                    if (condition_o12 != None):
                                                        client.new_order(
                                                            symbol=symbol, positionSide="SHORT", side="SELL", type="MARKET", quantity=round(minqty, 3))
                                                        write_to_history(
                                                            {"positionSide": "SHORT", "side": "SELL", "remark": "2", "key": api_use['key'], "opentime": int(opentime),
                                                             "condition": str(condition_o11)+"_"+str(condition_o12)})

                                            elif (abs(float(usdt_p_s[0]['positionAmt'])) < 2.5*minqty and abs(float(usdt_p_l[0]['positionAmt'])) < 2.9*minqty and opentrades >= 3):
                                                if ((s3 > r3op and s3 > mark_price) or
                                                    (r3 < s3op and r3 < mark_price) or
                                                        (unRealizedProfitPercentOpenningShort >= 2.6)):
                                                    client.new_order(
                                                        symbol=symbol, positionSide="SHORT", side="SELL", type="MARKET", quantity=round(minqty, 3))
                                                    write_to_history(
                                                        {"positionSide": "SHORT", "side": "SELL", "remark": "3", "key": api_use['key'], "opentime": int(opentime)})

                        # Close Safe with Lossable
                        if abs(float(usdt_p_s[0]['positionAmt'])) > minqty*1.5 or abs(float(usdt_p_l[0]['positionAmt'])) > minqty*1.5:

                            lastposition = client.get_account_trades(
                                symbol=symbol, limit=25)
                            last_sp = list(filter(lambda x: x['positionSide'] ==
                                                  "SHORT" and x['side'] == "SELL", lastposition))
                            last_lp = list(filter(lambda x: x['positionSide'] ==
                                                  "LONG" and x['side'] == "BUY", lastposition))

                            if (rsiMAConState == "UP" and rsiMAState == "UP") or (pmeanlineState == "UP"):
                                if abs(float(usdt_p_s[0]['positionAmt'])) >= minqty*1.5:
                                    if last_sp.__len__() == 0 or last_sp.__len__() > 0:
                                        if last_sp.__len__() == 0 or (int(time.time() * 1000) - last_sp[-1]['time'] > 3600000*2):
                                            if (unRealizedProfitOpenningShort > 0 or ((float(usdt_p_s[0]['entryPrice']) - mark_price)*minqty > lossable_margin*0.5 and lossable >= 75)) and unRealizedProfitPercentOpenningShort < 0.6:
                                                write_to_history(
                                                    {"positionSide": "SHORT", "side": "BUY", "remark": "CLOSESAFE_WITH_LOSSABLE", "key": api_use['key'], "profitPercent": unRealizedProfitPercentOpenningShort, "profit": unRealizedProfitOpenningShort})
                                                client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                                                 type="MARKET", quantity=abs(round(minqty, 3)))

                            if (rsiMAConState == "DOWN" and rsiMAState == "DOWN") or (pmeanlineState == "DOWN"):
                                if abs(float(usdt_p_l[0]['positionAmt'])) >= minqty*1.5:
                                    if last_lp.__len__() == 0 or last_lp.__len__() > 0:
                                        if last_lp.__len__() == 0 or (int(time.time() * 1000) - last_lp[-1]['time'] > 3600000*2):
                                            if (unRealizedProfitOpenningLong > 0 or ((mark_price - float(usdt_p_l[0]['entryPrice']))*minqty > lossable_margin*0.5 and lossable >= 75)) and unRealizedProfitPercentOpenningLong < 0.6:
                                                write_to_history(
                                                    {"positionSide": "LONG", "side": "SELL", "remark": "CLOSESAFE_WITH_LOSSABLE", "key": api_use['key'], "profitPercent": unRealizedProfitPercentOpenningLong, "profit": unRealizedProfitOpenningLong})
                                                client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                                                 type="MARKET", quantity=abs(round(minqty, 3)))

                else:

                    unRealizedProfitOpenningLong = float(
                        usdt_p_l[0]["unRealizedProfit"])
                    isolatedWalletOpenningLong = float(
                        usdt_p_l[0]["isolatedWallet"])
                    if isolatedWalletOpenningLong > 0:
                        unRealizedProfitPercentOpenningLong = unRealizedProfitOpenningLong * \
                            100 / isolatedWalletOpenningLong

                    unRealizedProfitOpenningShort = float(
                        usdt_p_s[0]["unRealizedProfit"])
                    isolatedWalletOpenningShort = float(
                        usdt_p_s[0]["isolatedWallet"])
                    if isolatedWalletOpenningShort > 0:
                        unRealizedProfitPercentOpenningShort = unRealizedProfitOpenningShort * \
                            100 / isolatedWalletOpenningShort

                    # CLOSE
                    if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
                        if ((mark_price - float(usdt_p_l[0]['entryPrice']))*minqty > lossable_margin or unRealizedProfitOpenningLong > 0) and lossable >= 75:
                            if ((rsiMAState == "DOWN" and float(message['rsi']) < float(message['rsiMA']) and mark_price < open) or
                                (barstatus == "DOWN" and mark_price < open) or
                                (rsiCrossState == "DOWN") or
                                    (float(message['rsi']) >= 70 or float(message['rsiMA']) >= 70 or float(message['rsiMA15']) >= 70)):
                                client.cancel_open_orders(symbol=symbol)
                                client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                                 type="MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
                                write_to_history(
                                    {"positionSide": "LONG", "side": "SELL", "remark": "CLOSE_WITH_NO_TRADE_1", "key": api_use['key'], "profitPercent": unRealizedProfitPercentOpenningLong, "profit": unRealizedProfitOpenningLong})
                        else:
                            if unRealizedProfitOpenningLong >= 0.45 or (unRealizedProfitOpenningLong > 0 and ('forceclose' in message and float(message['forceclose']) == 2)):
                                client.cancel_open_orders(symbol=symbol)
                                client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                                 type="MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
                                write_to_history(
                                    {"positionSide": "LONG", "side": "SELL", "remark": "CLOSE_WITH_NO_TRADE_2", "key": api_use['key'], "profitPercent": unRealizedProfitPercentOpenningLong, "profit": unRealizedProfitOpenningLong})

                    if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
                        if ((float(usdt_p_s[0]['entryPrice']) - mark_price)*minqty > lossable_margin or unRealizedProfitOpenningShort > 0) and lossable >= 75:
                            if ((rsiMAState == "UP" and float(message['rsi']) > float(message['rsiMA']) and mark_price > open) or
                                (rsiCrossState == "UP") or
                                (barstatus == "UP" and mark_price > open) or
                                    (float(message['rsi']) <= 30 or float(message['rsiMA']) <= 30 or float(message['rsiMA15']) <= 30)):
                                client.cancel_open_orders(symbol=symbol)
                                client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                                 type="MARKET", quantity=round(minqty, 3))
                                write_to_history(
                                    {"positionSide": "SHORT", "side": "BUY", "remark": "CLOSE_WITH_NO_TRADE_1", "key": api_use['key'], "profitPercent": unRealizedProfitPercentOpenningShort, "profit": unRealizedProfitOpenningShort})
                        else:
                            if unRealizedProfitOpenningShort >= 0.45 or (unRealizedProfitOpenningShort > 0 and ('forceclose' in message and float(message['forceclose']) == 1)):
                                client.cancel_open_orders(symbol=symbol)
                                client.new_order(symbol=symbol, positionSide="SHORT", side="BUY", type="MARKET", quantity=abs(
                                    float(usdt_p_s[0]['positionAmt'])))
                                write_to_history(
                                    {"positionSide": "SHORT", "side": "BUY", "remark": "CLOSE_WITH_NO_TRADE_2", "key": api_use['key'], "profitPercent": unRealizedProfitPercentOpenningShort, "profit": unRealizedProfitOpenningShort})

                # OPPOSITE_OPEN

                if abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*1.5 and abs(float(usdt_p_s[0]['positionAmt'])) < (minqty)*2.5 and abs(float(usdt_p_l[0]['positionAmt'])) == 0:
                    if (float(message['rsiMA15']) <= 30 or (float(message['rsiMA15']) <= 35 and float(message['rsi15']) <= 30)) and rsiMAConState == "UP" and barstatus == "UP" and low > s3:
                        client.cancel_open_orders(symbol=symbol)
                        client.new_order(symbol=symbol, positionSide="LONG",
                                         side="BUY", type="MARKET", quantity=round(minqty, 3))
                        write_to_history(
                            {"positionSide": "LONG", "side": "BUY", "remark": "OPPOSITE_OPEN", "key": api_use['key'], "profitPercent": unRealizedProfitPercentLong, "profit": unRealizedProfitLong})

                if abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*1.5 and abs(float(usdt_p_l[0]['positionAmt'])) < (minqty)*2.5 and abs(float(usdt_p_s[0]['positionAmt'])) == 0:
                    if (float(message['rsiMA15']) >= 70 or (float(message['rsiMA15']) >= 65 and float(message['rsi15']) >= 70)) and rsiMAConState == "DOWN" and barstatus == "DOWN" and high < r3:
                        client.cancel_open_orders(symbol=symbol)
                        client.new_order(symbol=symbol, positionSide="SHORT",
                                         side="SELL", type="MARKET", quantity=round(minqty, 3))
                        write_to_history(
                            {"positionSide": "SHORT", "side": "SELL", "remark": "OPPOSITE_OPEN", "key": api_use['key'], "profitPercent": unRealizedProfitPercentShort, "profit": unRealizedProfitShort})

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
            unRealizedProfitLong = 0
            unRealizedProfitShort = 0
            openorderLong = abs(float(usdt_p_l[0]["positionAmt"])) > 0
            openorderShort = abs(float(usdt_p_s[0]["positionAmt"])) > 0
            tp_long = 0
            tp_short = 0
            filled_order_long = 0

            # CLOSE SAFE WRONG SIZE TREND BREAK LONG
            if openorderLong:

                unRealizedProfitLong = float(
                    usdt_p_l[0]["unRealizedProfit"])
                isolatedWallet = float(
                    usdt_p_l[0]["isolatedWallet"])
                if isolatedWallet > 0:
                    unRealizedProfitPercentLong = unRealizedProfitLong * \
                        100 / isolatedWallet
                sumprofitlast100long = sum(list(map(lambda x: float(
                    x['realizedPnl']), curr_openning_cumprofit['long_sell_last100'])))

                if ((sumprofitlast100long > 0 and abs(float(usdt_p_l[0]['unRealizedProfit'])) < sumprofitlast100long*0.5) or
                    (mark_price - float(usdt_p_l[0]['entryPrice']))*minqty > lossable_margin or
                    (mark_price - float(usdt_p_l[0]['entryPrice'])) > 0 or
                        (abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*1.5 and
                         (float(message['rsiMA']) > 32.5) and
                         (close < open) and
                         (not (positionSide == "LONG" and opentrades >= 2)) and
                         ((float(usdt_p_l[0]['entryPrice']) - r3 > r3 - pmeanline) or (positionSide == "SHORT" and opentrades >= 2)))):
                    if mark_price < s3 and s3 < sp and r1 > sp and high < s3 and rsiMAState == "DOWN" and rsiMAConState == "DOWN" and pmeanlineState == "DOWN" and barstatus == "DOWN":
                        client.cancel_open_orders(symbol=symbol)
                        client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                         type="MARKET", quantity=round(minqty, 3))
                        write_to_history(
                            {"positionSide": "LONG", "side": "SELL", "remark": "CLOSE_SAFE_TRENDBREAK", "key": api_use['key'], "profitPercent": unRealizedProfitPercentLong, "profit": unRealizedProfitLong})

                # CLOSESAE TO MAKE AVERAGE PROFIT
                if (openprice != 0 or positionSide == "SHORT") and curr_openning_cumprofit['sum_neg_long'] == 0 and (curr_openning_cumprofit['sum_pos_long']) > 0 and (curr_openning_cumprofit['sum_pos_long'])*100 / abs(float(usdt_p_l[0]["isolatedWallet"])) < 0.6:
                    if (curr_openning_cumprofit['sum_pos_long'] + unRealizedProfitLong)*100 / abs(float(usdt_p_l[0]["isolatedWallet"])) > 0.6:
                        if positionSide == "SHORT" or (openprice != 0 and abs(float(usdt_p_l[0]["entryPrice"])) > (highest_long + openprice)*0.5):
                            client.cancel_open_orders(symbol=symbol)
                            client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                             type="MARKET", quantity=round(minqty, 3))
                            write_to_history(
                                {"positionSide": "LONG", "side": "SELL", "remark": "CLOSE_MAKECUM_TOAVERAGE", "key": api_use['key'], "profitPercent": unRealizedProfitPercentLong, "profit": unRealizedProfitLong})

            # CLOSE SAFE WRONG SIZE TREND BREAK SHORT
            if openorderShort:

                unRealizedProfitShort = float(
                    usdt_p_s[0]["unRealizedProfit"])
                isolatedWallet = float(
                    usdt_p_s[0]["isolatedWallet"])
                if isolatedWallet > 0:
                    unRealizedProfitPercentShort = unRealizedProfitShort * \
                        100 / isolatedWallet
                sumprofitlast100short = sum(list(map(lambda x: float(
                    x['realizedPnl']), curr_openning_cumprofit['short_sell_last100'])))

                if ((sumprofitlast100short > 0 and abs(float(usdt_p_s[0]['unRealizedProfit'])) < sumprofitlast100short*0.5) or
                    (float(usdt_p_s[0]['entryPrice']) - mark_price)*minqty > lossable_margin or
                    (float(usdt_p_s[0]['entryPrice']) - mark_price) > 0 or
                        (abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*1.5 and
                         (float(message['rsiMA']) < 67.5) and
                         (close > open) and
                         (not (positionSide == "SHORT" and opentrades >= 2)) and
                         ((pmeanline-s3 < s3 - float(usdt_p_s[0]['entryPrice'])) or (positionSide == "LONG" and opentrades >= 2)))):
                    if mark_price > r3 and r3 > rt and s1 < rt and low > r3 and rsiMAState == "UP" and rsiMAConState == "UP" and pmeanlineState == "UP" and barstatus == "UP":
                        client.cancel_open_orders(symbol=symbol)
                        client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                         type="MARKET", quantity=round(minqty, 3))
                        write_to_history(
                            {"positionSide": "SHORT", "side": "BUY", "remark": "CLOSE_SAFE_TRENDBREAK", "key": api_use['key'], "profitPercent": unRealizedProfitPercentLong, "profit": unRealizedProfitLong})

                # CLOSESAE TO MAKE AVERAGE PROFIT
                if (openprice != 0 or positionSide == "LONG") and curr_openning_cumprofit['sum_neg_short'] == 0 and curr_openning_cumprofit['sum_pos_short'] > 0 and (curr_openning_cumprofit['sum_pos_short'])*100 / abs(float(usdt_p_l[0]["isolatedWallet"])) < 0.6:
                    if (curr_openning_cumprofit['sum_pos_short'] + unRealizedProfitShort)*100 / abs(float(usdt_p_s[0]["isolatedWallet"])) > 0.6:
                        if positionSide == "LONG" or (openprice != 0 and (lowest_short + openprice)*0.5 > abs(float(usdt_p_s[0]["entryPrice"]))):
                            client.cancel_open_orders(symbol=symbol)
                            client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                             type="MARKET", quantity=round(minqty, 3))
                            write_to_history(
                                {"positionSide": "SHORT", "side": "BUY", "remark": "CLOSE_MAKECUM_TOAVERAGE", "key": api_use['key'], "profitPercent": unRealizedProfitPercentShort, "profit": unRealizedProfitShort})

            # LONG_STOP_PRICE
            if openorderLong:

                sumprofitlast100long = sum(list(map(lambda x: float(
                    x['realizedPnl']), curr_openning_cumprofit['long_sell_last100'])))

                if isinstance(order_history, list) and len(order_history) > 0:
                    new_orders_long = [
                        order for order in order_history if ((order.get("status") == "NEW" or order.get("status") == "CANCELED") and order.get("positionSide") == "LONG")]
                    filled_orders = [
                        order for order in order_history if (order.get("status") == "FILLED" and order.get("positionSide") == "LONG")]

                    # CLOSE SAFE WRONG SIZE TREND CHANGE
                    if len(filled_orders) == 0 or (current_milliseconds - filled_orders[-1]["time"] > (minute_limit*60*1000)):
                        if (abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*1.5 or
                            (unRealizedProfitShort != 0 and unRealizedProfitShort > abs(unRealizedProfitLong)) or
                            (mark_price > pmeanline) or
                                (sumprofitlast100long > 0 and abs(float(usdt_p_l[0]['unRealizedProfit'])) < sumprofitlast100long*0.5)):
                            if mark_price > (rt + sp)*0.5 and s3 > (rt + sp)*0.5 and rsiMAConState == "DOWN" and rsiMAState == "DOWN" and pmeanlineState == "DOWN" and barstatus == "DOWN":
                                client.cancel_open_orders(symbol=symbol)
                                client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                                 type="MARKET", quantity=round(minqty, 3))
                                write_to_history(
                                    {"positionSide": "LONG", "side": "SELL", "remark": "TREND_CHANGE_AT_HIGH_RISK", "key": api_use['key'], "profitPercent": unRealizedProfitPercentLong, "profit": unRealizedProfitLong})

                else:

                    # CLOSE SAFE WRONG SIZE TREND CHANGE
                    if (abs(float(usdt_p_l[0]['positionAmt'])) >= (minqty)*1.5 or
                        (unRealizedProfitShort != 0 and unRealizedProfitShort > abs(unRealizedProfitLong)) or
                            (mark_price > pmeanline) or
                            (sumprofitlast100long > 0 and abs(float(usdt_p_l[0]['unRealizedProfit'])) < sumprofitlast100long*0.5)):
                        if mark_price > (rt + sp)*0.5 and s3 > (rt + sp)*0.5 and rsiMAConState == "DOWN" and rsiMAState == "DOWN" and pmeanlineState == "DOWN" and barstatus == "DOWN":
                            client.cancel_open_orders(symbol=symbol)
                            client.new_order(symbol=symbol, positionSide="LONG", side="SELL",
                                             type="MARKET", quantity=round(minqty, 3))
                            write_to_history(
                                {"positionSide": "LONG", "side": "SELL", "remark": "TREND_CHANGE_AT_HIGH_RISK", "key": api_use['key'], "profitPercent": unRealizedProfitPercentLong, "profit": unRealizedProfitLong})

            # SHORT_STOP_PRICE
            if openorderShort:
                sumprofitlast100short = sum(list(map(lambda x: float(
                    x['realizedPnl']), curr_openning_cumprofit['short_sell_last100'])))

                if isinstance(order_history, list) and len(order_history) > 0:
                    new_orders_short = [
                        order for order in order_history if ((order.get("status") == "NEW" or order.get("status") == "CANCELED") and order.get("positionSide") == "SHORT")]
                    filled_orders = [
                        order for order in order_history if (order.get("status") == "FILLED" and order.get("positionSide") == "SHORT")]

                    # CLOSE SAFE WRONG SIZE TREND CHANGE
                    if len(filled_orders) == 0 or (current_milliseconds - filled_orders[-1]["time"] > (minute_limit*60*1000)):
                        if (abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*1.5 or
                            (unRealizedProfitLong != 0 and unRealizedProfitLong > abs(unRealizedProfitShort)) or
                            (mark_price < pmeanline) or
                                (sumprofitlast100short > 0 and abs(float(usdt_p_s[0]['unRealizedProfit'])) < sumprofitlast100short*0.5)):
                            if mark_price < (rt + sp)*0.5 and r3 < (rt + sp)*0.5 and rsiMAConState == "UP" and rsiMAState == "UP" and pmeanlineState == "UP" and barstatus == "UP":
                                client.cancel_open_orders(symbol=symbol)
                                client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                                 type="MARKET", quantity=round(minqty, 3))
                                write_to_history(
                                    {"positionSide": "SHORT", "side": "BUY", "remark": "TREND_CHANGE_AT_HIGH_RISK", "key": api_use['key'], "profitPercent": unRealizedProfitPercentShort, "profit": unRealizedProfitShort})
                else:

                    # CLOSE SAFE WRONG SIZE TREND CHANGE
                    if (abs(float(usdt_p_s[0]['positionAmt'])) >= (minqty)*1.5 or
                        (unRealizedProfitLong != 0 and unRealizedProfitLong > abs(unRealizedProfitShort)) or
                        (mark_price < pmeanline) or
                            (sumprofitlast100short > 0 and abs(float(usdt_p_s[0]['unRealizedProfit'])) < sumprofitlast100short*0.5)):
                        if mark_price < (rt + sp)*0.5 and r3 < (rt + sp)*0.5 and rsiMAConState == "UP" and rsiMAState == "UP" and pmeanlineState == "UP" and barstatus == "UP":
                            client.cancel_open_orders(symbol=symbol)
                            client.new_order(symbol=symbol, positionSide="SHORT", side="BUY",
                                             type="MARKET", quantity=round(minqty, 3))
                            write_to_history(
                                {"positionSide": "SHORT", "side": "BUY", "remark": "TREND_CHANGE_AT_HIGH_RISK", "key": api_use['key'], "profitPercent": unRealizedProfitPercentShort, "profit": unRealizedProfitShort})

            tp_order(openbar, mark_price, open, close, max_profit_check, pmeanline, pmop, unRealizedProfitPercentLong, unRealizedProfitPercentShort, new_orders_long,
                     new_orders_short, usdt_p_l, usdt_p_s, low, high, r3, s3, r1, s1, rt, sp, pmeanlineState, rsiMAState, rsiMAConState, highest_long, lowest_short, client, symbol)

            current_time = datetime.now()
            updated_time = current_time + timedelta(hours=7)
            formatted_time = updated_time.strftime("%Y-%m-%d %H:%M:%S")
            timestamp_seconds = current_time.timestamp()
            timestamp_milliseconds = int(timestamp_seconds * 1000)

            update_api_status({"key": api_use['key'],
                               "time": formatted_time,
                               "timestamp": timestamp_milliseconds,
                               "opentime": int(opentime) if opentime != None else 0,
                               "positionSide": positionSide,
                               "condition": str(condition_o1)+"_"+str(condition_o2)+"_"+str(condition_o3)+"_"+str(condition_o4)+"_"+str(condition_o5)+"_"+str(condition_o11)+"_"+str(condition_o12)})

    return {'balances': balances, 'lossable_margin': lossable_margin}

    # return {
    #     'balance': usdt_b_all,
    #     'symbol': symbol,
    #     'short': usdt_p_s,
    #     'long': usdt_p_l,
    #     'mark_price': mark_price,
    #     'minqty': minqty,
    #     'TPL': unRealizedProfitPercentLong > max_profit_check and low <= r3,
    #     'TPS': unRealizedProfitPercentShort > max_profit_check and high >= s3,
    #     'TPP_L': tp_long,
    #     'TPP_S': tp_short,
    #     'winrate': winrate,
    #     'lossable': lossable,
    #     'win_margin': win_margin,
    #     'loss_margin': loss_margin,
    #     'unRealizedProfitOpenningShort': unRealizedProfitOpenningShort,
    #     'unRealizedProfitOpenningLong': unRealizedProfitOpenningLong,
    #     'winrate_margin': winrate_margin,
    #     'lossable_margin': lossable_margin,
    # }


def tp_order(openbar, mark_price, open, close, max_profit_check, pmeanline, pmop, unRealizedProfitPercentLong, unRealizedProfitPercentShort, new_orders_long, new_orders_short, usdt_p_l, usdt_p_s, low, high, r3, s3, r1, s1, rt, sp, pmeanlineState, rsiMAState, rsiMAConState, highest_long, lowest_short, client: UMFutures, symbol="ETHUSDT"):
    closeprice = 0
    # LONG
    if float(usdt_p_l[0]['positionAmt']) > 0 and unRealizedProfitPercentLong > 0.2:
        if s3 > (rt+sp)*0.5 or (pmeanlineState == "DOWN" and rsiMAConState == "DOWN" and rsiMAState == "DOWN"):
            if ((unRealizedProfitPercentLong > max_profit_check and (low <= r3 or mark_price < open)) or
                    (rsiMAState == "DOWN" or pmeanlineState == "DOWN") or
                    (unRealizedProfitPercentLong > 0.2 and float(usdt_p_l[0]['entryPrice']) > r1 and (mark_price < open or close < open)) or
                    (unRealizedProfitPercentLong > 0.2 and float(usdt_p_l[0]['entryPrice']) > r3 and openbar >= 8)):
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

        # SAVE REVERSE LONG
        if unRealizedProfitPercentLong >= 0.15 and unRealizedProfitPercentLong < 0.6 and (len(new_orders_long) == 0 or new_orders_long[-1]['status'] == "CANCELED"):
            if high > pmeanline and float(usdt_p_l[0]['entryPrice']) < pmeanline and (pmeanline < pmop or pmeanlineState == "DOWN" or rsiMAConState == "DOWN" or rsiMAState == "DOWN"):

                closeprice = None

                if len(new_orders_long) > 0 and new_orders_long[-1]['status'] == "NEW":
                    last_stop_price = float(new_orders_long[-1]['stopPrice'])
                    closeprice_by_mark = (float(usdt_p_l[0]['markPrice']) +
                                          float(usdt_p_l[0]['entryPrice']))*0.5
                    closeprice_by_highest = (highest_long +
                                             float(usdt_p_l[0]['entryPrice']))*0.5
                    closeprice = closeprice_by_highest if (
                        closeprice_by_highest > closeprice_by_mark and mark_price > closeprice_by_highest) else closeprice_by_mark

                closeprice = float(
                    usdt_p_l[0]['entryPrice']) * 1.015 if closeprice == None or mark_price < closeprice else closeprice

                if mark_price > closeprice:
                    client.cancel_open_orders(symbol=symbol)
                    client.new_order(symbol=symbol, positionSide="LONG", side="SELL", stopPrice=int(closeprice),
                                     type="STOP_MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))

        # CANCEL
        if low > r3 and unRealizedProfitPercentLong > 0.6 and not (mark_price < open):
            client.cancel_open_orders(symbol=symbol)

    # SHORT
    if abs(float(usdt_p_s[0]['positionAmt'])) > 0 and unRealizedProfitPercentShort > 0.2:
        if r3 < (rt+sp)*0.5 or (pmeanlineState == "UP" and rsiMAConState == "UP" and rsiMAState == "UP"):
            if ((unRealizedProfitPercentShort > max_profit_check and (high >= s3 or mark_price > open)) or
                    (rsiMAState == "UP" or pmeanlineState == "UP") or
                    (unRealizedProfitPercentShort > 0.2 and float(usdt_p_s[0]['entryPrice']) < s1 and (mark_price > open or close > open)) or
                    (unRealizedProfitPercentShort > 0.2 and float(usdt_p_s[0]['entryPrice']) < s3 and openbar >= 8)):
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

        # SAVE REVERSE SHORT
        if unRealizedProfitPercentShort >= 0.15 and unRealizedProfitPercentShort < 0.6 and (len(new_orders_short) == 0 or new_orders_short[-1]['status'] == "CANCELED"):
            if low < pmeanline and float(usdt_p_s[0]['entryPrice']) > pmeanline and (pmeanline > pmop or pmeanlineState == "UP" or rsiMAConState == "UP" or rsiMAState == "UP"):

                closeprice = None

                if len(new_orders_short) > 0 and new_orders_short[-1]['status'] == "NEW":
                    last_stop_price = float(new_orders_short[-1]['stopPrice'])
                    closeprice_by_mark = (float(usdt_p_s[0]['markPrice']) +
                                          float(usdt_p_s[0]['entryPrice']))*0.5
                    closeprice_by_lowest = (lowest_short +
                                            float(usdt_p_s[0]['entryPrice']))*0.5
                    closeprice = closeprice_by_lowest if (
                        closeprice_by_lowest < closeprice_by_mark and mark_price < closeprice_by_lowest) else closeprice_by_mark

                closeprice = float(
                    usdt_p_s[0]['entryPrice']) * 0.985 if closeprice == None or mark_price > closeprice else closeprice

                if mark_price < closeprice:
                    client.cancel_open_orders(symbol=symbol)
                    client.new_order(symbol=symbol, positionSide="SHORT", side="BUY", stopPrice=int(closeprice),
                                     type="STOP_MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))

        # CANCEL
        if high < s3 and unRealizedProfitPercentShort > 0.6 and not (mark_price > open):
            client.cancel_open_orders(symbol=symbol)


def lossable_calculate(positions, symbol="ETHUSDT"):

    positions = list(filter(lambda x: float(x['realizedPnl']) != 0, positions))
    win_margin = 0
    loss_margin = 0
    wincount = 0
    losscount = 0
    winrate = 0
    lossable = 0
    winrate_margin = 0
    lossable_margin = 0

    accumulated_data = defaultdict(float)

    for entry in positions:
        orderId = entry['orderId']
        realizedPnl = float(entry['realizedPnl'])
        accumulated_data[orderId] += realizedPnl

    unique_positions = [{'orderId': orderId, 'realizedPnl': accumulated_data[orderId]}
                        for orderId in accumulated_data]

    for p in reversed(unique_positions):
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
        lossable_margin = -((win_margin/4) - loss_margin)  # 75% win-margin

    return winrate, lossable, winrate_margin, lossable_margin, win_margin, loss_margin


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


def write_to_history(obj):
    # Get the current time
    current_time = datetime.now()
    updated_time = current_time + timedelta(hours=7)
    formatted_time = updated_time.strftime("%Y-%m-%d %H:%M:%S")
    ref_history.child(formatted_time).set(obj)


def update_api_status(obj):
    key = obj["key"]
    existing_data = ref_apistatus.child(key).get()
    if existing_data is not None:
        ref_apistatus.child(key).delete()
    ref_apistatus.child(key).set(obj)


@app.route("/firebase-test-read", methods=["GET"])
def firebase_test_read():
    ref = db.reference('test')
    return ref.get()
    # return get_key_active()


@app.route("/firebase-test-write", methods=["GET"])
def firebase_test_write():
    write_to_history({"positionSide": "TEST", "side": "TEST",
                     "remark": "TEST"})
    return True


@app.route("/firebase-history-order", methods=["POST"])
def firebase_history_order():

    requestData = app.current_request
    message = requestData.json_body
    symbol = "ETHUSDT"

    api_use = None
    data = ref_key.get()
    data = list(filter(lambda x: x != None, data))
    for obj in data:
        if 'key' in obj and obj['key'] == message['key']:
            api_use = obj
            break

    client = UMFutures(api_use['key'], api_use['secret'])
    curr_openning_cumprofit = get_current_openning_cumprofit(
        client=client, symbol=symbol)
    return curr_openning_cumprofit


def get_current_openning_cumprofit(client: UMFutures, symbol="ETHUSDT"):

    binance_results = client.get_account_trades(symbol=symbol, limit=100)

    # query = ref_history.order_by_key().limit_to_last(20)
    query = ref_history.order_by_child(
        'key').equal_to(client.key).limit_to_last(50)
    firebase_results = query.get()

    open_position = []
    long_buy_filtered = []
    short_buy_filtered = []
    long_sell_filtered = []
    short_sell_filtered = []
    long_sell_last100 = []
    short_sell_last100 = []
    last_openning_long = None
    last_openning_short = None
    sum_pos_long = 0
    sum_neg_long = 0
    sum_pos_short = 0
    sum_neg_short = 0

    for timestamp, record in firebase_results.items():
        if (record["positionSide"] == "LONG" and record["side"] == "BUY") or (record["positionSide"] == "SHORT" and record["side"] == "SELL"):
            open_position.append({
                "timestamp": timestamp,
                "positionSide": record["positionSide"],
                "side": record["side"],
                "opentime": record.get("opentime", None)
            })

    long_sell_last100 = list(filter(
        lambda x: x['positionSide'] == "LONG" and x['side'] == "SELL", binance_results))
    short_sell_last100 = list(filter(
        lambda x: x['positionSide'] == "SHORT" and x['side'] == "BUY", binance_results))

    long_buy_filtered = list(filter(
        lambda x: 'opentime' in x and x['opentime'] != None and x['positionSide'] == "LONG" and x['side'] == "BUY", open_position))
    if long_buy_filtered.__len__() > 0:
        last_openning_long = long_buy_filtered[-1]
        long_sell_filtered = list(filter(
            lambda x: x['positionSide'] == "LONG" and x['side'] == "SELL" and x['time'] >= last_openning_long['opentime'], binance_results))
        sum_pos_long = sum(list(map(lambda x: float(x['realizedPnl']), list(
            filter(lambda x: float(x['realizedPnl']) > 0, long_sell_filtered)))))
        sum_neg_long = sum(list(map(lambda x: float(x['realizedPnl']), list(
            filter(lambda x: float(x['realizedPnl']) < 0, long_sell_filtered)))))
    if long_sell_filtered.__len__() == 0 and long_buy_filtered.__len__() >= 2:
        last_openning_long = long_buy_filtered[-2]
        long_sell_filtered = list(filter(
            lambda x: x['positionSide'] == "LONG" and x['side'] == "SELL", binance_results))
        sum_pos_long = sum(list(map(lambda x: float(x['realizedPnl']), list(
            filter(lambda x: float(x['realizedPnl']) > 0, long_sell_filtered)))))
        sum_neg_long = sum(list(map(lambda x: float(x['realizedPnl']), list(
            filter(lambda x: float(x['realizedPnl']) < 0, long_sell_filtered)))))

    short_buy_filtered = list(filter(
        lambda x: 'opentime' in x and x['opentime'] != None and x['positionSide'] == "SHORT" and x['side'] == "SELL", open_position))
    if short_buy_filtered.__len__() > 0:
        last_openning_short = short_buy_filtered[-1]
        short_sell_filtered = list(filter(
            lambda x: x['positionSide'] == "SHORT" and x['side'] == "BUY" and x['time'] >= last_openning_short['opentime'], binance_results))
        sum_pos_short = sum(list(map(lambda x: float(x['realizedPnl']), list(
            filter(lambda x: float(x['realizedPnl']) > 0, short_sell_filtered)))))
        sum_neg_short = sum(list(map(lambda x: float(x['realizedPnl']), list(
            filter(lambda x: float(x['realizedPnl']) < 0, short_sell_filtered)))))
    if short_sell_filtered.__len__() == 0 and short_buy_filtered.__len__() >= 2:
        last_openning_short = short_buy_filtered[-2]
        short_sell_filtered = list(filter(
            lambda x: x['positionSide'] == "SHORT" and x['side'] == "BUY" and x['time'] >= last_openning_short['opentime'], binance_results))
        sum_pos_short = sum(list(map(lambda x: float(x['realizedPnl']), list(
            filter(lambda x: float(x['realizedPnl']) > 0, short_sell_filtered)))))
        sum_neg_short = sum(list(map(lambda x: float(x['realizedPnl']), list(
            filter(lambda x: float(x['realizedPnl']) < 0, short_sell_filtered)))))

    return {"sum_pos_long": sum_pos_long,
            "sum_neg_long": sum_neg_long,
            "sum_pos_short": sum_pos_short,
            "sum_neg_short": sum_neg_short,
            "long_sell_filtered": long_sell_filtered,
            "last_openning_long": last_openning_long,
            "short_sell_filtered": short_sell_filtered,
            "last_openning_short": last_openning_short,
            "long_sell_last100": long_sell_last100,
            "short_sell_last100": short_sell_last100}


def round_to_nearest_15_minutes(timestamp_ms):
    # Convert milliseconds to seconds
    timestamp_sec = timestamp_ms / 1000

    # Convert timestamp to datetime object
    dt = datetime.utcfromtimestamp(timestamp_sec)

    # Round the datetime object to the nearest 15-minute interval
    rounded_minute = (dt.minute + 7.5) // 15 * 15
    rounded_dt = dt.replace(minute=int(rounded_minute),
                            second=0, microsecond=0)

    # Convert rounded datetime back to milliseconds
    rounded_timestamp_ms = int(rounded_dt.timestamp() * 1000)

    return rounded_timestamp_ms


# @app.route("/firebase-change-history-key", methods=["GET"])
# def change_format_key():

#     keys = ref_history.get().keys()
#     for key in keys:
#         old_key = key
#         old_datetime_str = datetime.strptime(old_key, "%d-%m-%Y %H:%M:%S")
#         new_key = old_datetime_str.strftime("%Y-%m-%d %H:%M:%S")

#         data = ref_history.child(old_key).get()
#         ref_history.child(old_key).delete()
#         ref_history.child(new_key).set(data)
#
# @app.route("/file-test", methods=["GET"])
# def file_test():

#     file_path = 'binance-key.json'
#     with open(file_path, 'r') as file:
#         json_data = json.load(file)

#     keys = json_data['keys']
#     return keys[0]["key"]
