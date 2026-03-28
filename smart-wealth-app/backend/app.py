from flask import Flask, render_template, request, session
import yfinance as yf
import requests
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "smartwealth_secret_key_2024"  # needed for session history

@app.route("/")
def home():
    history = session.get("history", [])
    return render_template("index.html", history=history)

@app.route("/result", methods=["POST"])
def result():

    # -------- RISK INPUT --------
    risk = request.form.get("risk", "medium")

    # -------- USER INPUT --------
    income = float(request.form.get("income", 0))
    food = float(request.form.get("food", 0))
    rent = float(request.form.get("rent", 0))
    travel = float(request.form.get("travel", 0))
    shopping = float(request.form.get("shopping", 0))
    entertainment = float(request.form.get("entertainment", 0))
    subscriptions = float(request.form.get("subscriptions", 0))
    utilities = float(request.form.get("utilities", 0))

    # -------- CALCULATIONS --------
    needs = food + rent + travel + utilities
    wants = shopping + entertainment + subscriptions
    total = needs + wants
    savings = income - total

    # -------- SUGGESTION --------
    if savings < 5000:
        suggestion = "Focus on saving more before investing."
    elif savings < 15000:
        suggestion = "Invest in SIP + Gold."
    else:
        suggestion = "Invest in Stocks + SIP + Gold."

    # -------- RISK-BASED STOCKS --------
    if risk == "low":
        stocks = {
            "HDFC Bank": "HDFCBANK.NS",
            "ITC": "ITC.NS",
            "HUL": "HINDUNILVR.NS",
            "SBI": "SBIN.NS"
        }
    elif risk == "medium":
        stocks = {
            "Reliance": "RELIANCE.NS",
            "Infosys": "INFY.NS",
            "ICICI Bank": "ICICIBANK.NS",
            "TCS": "TCS.NS",
            "L&T": "LT.NS"
        }
    else:
        stocks = {
            "Tata Motors": "TATAMOTORS.NS",
            "Wipro": "WIPRO.NS",
            "ONGC": "ONGC.NS",
            "Sun Pharma": "SUNPHARMA.NS",
            "Adani Enterprises": "ADANIENT.NS"
        }

    # -------- STOCK DATA + 30-DAY HISTORY --------
    stock_data = {}
    stock_units = {}
    stock_chart_data = {}   # {name: {labels: [...], prices: [...]}}
    stock_investment = savings * 0.4

    for name, ticker in stocks.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="30d")
            if not hist.empty:
                price = round(hist["Close"].iloc[-1], 2)
                # build chart series
                labels = [str(d.date()) for d in hist.index]
                prices = [round(p, 2) for p in hist["Close"].tolist()]
                stock_chart_data[name] = {"labels": labels, "prices": prices}
            else:
                price = 0
                stock_chart_data[name] = {"labels": [], "prices": []}
        except:
            price = 0
            stock_chart_data[name] = {"labels": [], "prices": []}

        stock_data[name] = price

    valid_stocks = {k: v for k, v in stock_data.items() if v > 0}
    per_stock = stock_investment / len(valid_stocks) if valid_stocks else 0

    for stock in stock_data:
        price = stock_data[stock]
        stock_units[stock] = round(per_stock / price, 2) if price > 0 else 0

    # -------- SIP --------
    try:
        mf_data = requests.get("https://api.mfapi.in/mf/119551").json()
        sip_nav = float(mf_data["data"][0]["nav"])
        # build SIP NAV history (last 30 entries)
        sip_history_raw = mf_data["data"][:30][::-1]
        sip_labels = [e["date"] for e in sip_history_raw]
        sip_navs = [float(e["nav"]) for e in sip_history_raw]
    except:
        sip_nav = 0
        sip_labels = []
        sip_navs = []

    sip_units = round((savings * 0.4) / sip_nav, 2) if sip_nav else 0

    # -------- GOLD --------
    try:
        gold_data = requests.get("https://api.metals.live/v1/spot").json()
        gold_usd = gold_data[0]["gold"]  # USD per troy oz
        # convert: 1 troy oz = 31.1035g, get INR rate
        fx = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
        inr_rate = fx["rates"].get("INR", 83)
        gold_price = round((gold_usd * inr_rate) / 31.1035, 2)  # INR per gram
    except:
        gold_price = 6000

    gold_units = round((savings * 0.2) / gold_price, 2) if gold_price else 0

    # -------- ALLOCATION DATA for doughnut chart --------
    allocation_labels = []
    allocation_values = []

    stock_total = savings * 0.4 if valid_stocks else 0
    if stock_total > 0:
        allocation_labels.append("Stocks")
        allocation_values.append(round(stock_total, 2))

    if sip_units > 0:
        allocation_labels.append("SIP")
        allocation_values.append(round(sip_units * sip_nav, 2))

    if gold_units > 0:
        allocation_labels.append("Gold")
        allocation_values.append(round(gold_units * gold_price, 2))

    # -------- SAVE TO SESSION HISTORY --------
    history_entry = {
        "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "income": income,
        "savings": round(savings, 2),
        "needs": round(needs, 2),
        "wants": round(wants, 2),
        "risk": risk,
        "suggestion": suggestion,
        "stocks": list(stock_data.keys()),
        "sip_nav": round(sip_nav, 2),
        "gold_price": round(gold_price, 2),
    }

    history = session.get("history", [])
    history.insert(0, history_entry)
    history = history[:10]   # keep last 10 analyses
    session["history"] = history

    # -------- RETURN --------
    return render_template("result.html",
                           savings=round(savings, 2),
                           needs=round(needs, 2),
                           wants=round(wants, 2),
                           income=income,
                           suggestion=suggestion,
                           stock_data=stock_data,
                           stock_units=stock_units,
                           stock_chart_data=json.dumps(stock_chart_data),
                           sip_nav=round(sip_nav, 2),
                           sip_units=sip_units,
                           sip_labels=json.dumps(sip_labels),
                           sip_navs=json.dumps(sip_navs),
                           gold_price=round(gold_price, 2),
                           gold_units=gold_units,
                           risk=risk,
                           allocation_labels=json.dumps(allocation_labels),
                           allocation_values=json.dumps(allocation_values),
                           history=history)

@app.route("/clear_history", methods=["POST"])
def clear_history():
    session.pop("history", None)
    return ("", 204)

if __name__ == "__main__":
    app.run(debug=True)