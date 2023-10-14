from chalice import Chalice
# from binance.client import Client
from binance.um_futures import UMFutures
from typing import Dict, Optional, List, Tuple
import time
import http.client
import json

app = Chalice(app_name='tradingview-webhook')


@app.route('/')
def index():
    return {'hello': 'world'}


@app.route("/get-account-balance", methods=["GET"])
def get_account_balance():
    client = UMFutures('bVXg4acFCMdpqbXZNhoLQyw3VgqNekfKLlEzZk9NGrmWvXd6iWyS9kQjyPQIOnxB',
                       'w5xL8MSwYnsNgkLNlxUw6bpJIPC1MWxak7NPLsDz6WK8nuQ0QgPNyREyrq2ShQqD')
    # request = app.current_request
    # message = request.json_body
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


@app.route("/order", methods=["POST"])
def order():
    client = UMFutures('bVXg4acFCMdpqbXZNhoLQyw3VgqNekfKLlEzZk9NGrmWvXd6iWyS9kQjyPQIOnxB',
                       'w5xL8MSwYnsNgkLNlxUw6bpJIPC1MWxak7NPLsDz6WK8nuQ0QgPNyREyrq2ShQqD')
    request = app.current_request
    message = request.json_body

    symbol = message['symbol']
    balance = client.balance()
    position_risk = client.get_position_risk(symbol=symbol)
    usdt_b = list(filter(lambda x: x['asset'] == "USDT", balance))[
        0]['balance']

    usdt_p_l = list(filter(
        lambda x: x['symbol'] == symbol and x['positionSide'] == "LONG", position_risk))
    usdt_p_s = list(filter(
        lambda x: x['symbol'] == symbol and x['positionSide'] == "SHORT", position_risk))

    mark_price = float(usdt_p_l[0]['markPrice'])
    minqty = round(
        (0.004*(float(usdt_p_l[0]['markPrice']))/float(usdt_b))*0.3, 3)

    opentrades = int(str(message['opentrades']))

    if opentrades > 0:

        positionSide = message['positionSide']
        barstatus = message['barstatus']
        openprice = float(str(message['openprice']))
        openbar = int(str(message['openbar']))
        s3 = float(str(message['s3']))
        s1 = float(str(message['s1']))
        r3 = float(str(message['r3']))
        r1 = float(str(message['r1']))

        if positionSide == "LONG":
            if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
                client.new_order(symbol=symbol, positionSide="SHORT", side=(
                    "BUY" if positionSide == "SHORT" else "SELL"), type="MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))
            if (abs(float(usdt_p_l[0]['positionAmt'])) < opentrades*minqty) and barstatus == "UP":
                if abs(float(usdt_p_l[0]['positionAmt'])) == 0:
                    client.new_order(symbol=symbol, positionSide=positionSide, side=(
                        "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                elif (abs(float(usdt_p_l[0]['positionAmt'])) < 1.5*minqty and opentrades <= 1) or mark_price < openprice:
                    if mark_price <= s1:
                        client.new_order(symbol=symbol, positionSide=positionSide, side=(
                            "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                elif (abs(float(usdt_p_l[0]['positionAmt'])) < 2.5*minqty and opentrades >= 2):
                    if mark_price <= s3:
                        client.new_order(symbol=symbol, positionSide=positionSide, side=(
                            "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))

        if positionSide == "SHORT":
            if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
                client.new_order(symbol=symbol, positionSide="LONG", side=(
                    "BUY" if positionSide == "SHORT" else "SELL"), type="MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))
            if (abs(float(usdt_p_s[0]['positionAmt'])) < opentrades*minqty) and barstatus == "DOWN":
                if abs(float(usdt_p_s[0]['positionAmt'])) == 0:
                    client.new_order(symbol=symbol, positionSide=positionSide, side=(
                        "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                elif (abs(float(usdt_p_s[0]['positionAmt'])) < 1.5*minqty and opentrades <= 1) or mark_price > openprice:
                    if mark_price >= r1:
                        client.new_order(symbol=symbol, positionSide=positionSide, side=(
                            "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))
                elif (abs(float(usdt_p_s[0]['positionAmt'])) < 2.5*minqty and opentrades >= 2):
                    if mark_price >= r3:
                        client.new_order(symbol=symbol, positionSide=positionSide, side=(
                            "BUY" if positionSide == "LONG" else "SELL"), type="MARKET", quantity=round(minqty, 3))

    else:
        if abs(float(usdt_p_s[0]['positionAmt'])) > 0:
            client.new_order(symbol=symbol, positionSide="SHORT", side=(
                "BUY" if positionSide == "SHORT" else "SELL"), type="MARKET", quantity=abs(float(usdt_p_s[0]['positionAmt'])))
        if abs(float(usdt_p_l[0]['positionAmt'])) > 0:
            client.new_order(symbol=symbol, positionSide="LONG", side=(
                "BUY" if positionSide == "SHORT" else "SELL"), type="MARKET", quantity=abs(float(usdt_p_l[0]['positionAmt'])))

    return {'message': float(usdt_p_s[0]['positionAmt'])}


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
