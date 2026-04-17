import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import anthropic
from datetime import date

# ---- SETTINGS ----
API_KEY = "your-api-key-here"

# ---- FETCH FULL S&P 500 TICKER LIST ----
print("Fetching S&P 500 ticker list...")
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
html = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers=headers).text
sp500_table = pd.read_html(pd.io.common.StringIO(html))
TICKERS = sp500_table[0]["Symbol"].tolist()
TICKERS = [t.replace(".", "-") for t in TICKERS]

# ---- STEP 1: GET STOCK DATA ----
print("Fetching stock data... (this may take 2-3 minutes for 500 stocks)")
raw_data = yf.download(TICKERS, period="2d", auto_adjust=True)
closing_prices = raw_data["Close"]
volumes = raw_data["Volume"]
pct_change = closing_prices.pct_change().iloc[-1] * 100
avg_volume = volumes.iloc[:-1].mean()
volume_change = ((volumes.iloc[-1] - avg_volume) / avg_volume * 100)
top10 = pct_change.nlargest(10)
bottom10 = pct_change.nsmallest(10)
all_stocks = pd.concat([top10, bottom10])

# Fetch company names
print("Fetching company names...")
company_names = {}
for ticker in all_stocks.index:
    try:
        info = yf.Ticker(ticker).info
        company_names[ticker] = info.get("shortName", ticker)
    except:
        company_names[ticker] = ticker

# ---- STEP 2: GENERATE CHARTS ----
print("Generating charts...")
os.makedirs("charts", exist_ok=True)

for ticker in all_stocks.index:
    data = yf.download(ticker, period="1mo", interval="1d", auto_adjust=True)
    closes = data["Close"]
    fig, ax = plt.subplots(figsize=(6, 3))
    change = all_stocks[ticker]
    line_color = "green" if change > 0 else "red"
    ax.plot(closes.index, closes.values, color=line_color, linewidth=2)
    ax.set_title(f"{ticker} — Last 30 Days", fontsize=11)
    ax.set_ylabel("Price (USD)")
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.tight_layout()
    plt.savefig(f"charts/{ticker}.png")
    plt.close()
    print(f"  Chart saved for {ticker}")

# ---- STEP 3: GET AI COMMENTARY ----
print("\nGenerating AI commentary...")
client = anthropic.Anthropic(api_key=API_KEY)

def get_commentary(ticker, pct_change, volume_change):
    prompt = f"""You are a financial analyst writing a brief daily market report.
Today's data for {ticker}:
- Price change: {pct_change:.2f}%
- Volume change vs average: {volume_change:.0f}%

Based purely on these statistics, write exactly 2 sentences of professional analysis.
Discuss what the magnitude of the price move and volume signal suggest about market sentiment and likely investor behaviour.
Do not reference specific news or events. Do not say you lack information.
Do not include any headings, titles, hashtags, or labels. Just write the 2 sentences directly."""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

commentaries = {}
for ticker in all_stocks.index:
    print(f"  Getting commentary for {ticker}...")
    vol_chg = volume_change[ticker] if ticker in volume_change else 0
    commentaries[ticker] = get_commentary(ticker, all_stocks[ticker], vol_chg)

# ---- STEP 4: BUILD THE PDF ----
print("\nBuilding PDF report...")
today = date.today().strftime("%B %d, %Y")
filename = f"stock_report_{date.today()}.pdf"

doc = SimpleDocTemplate(filename, pagesize=letter,
                        rightMargin=0.75*inch, leftMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)

styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle("title", fontSize=22, fontName="Helvetica-Bold",
                              spaceAfter=12, textColor=colors.HexColor("#1a1a2e"))
subtitle_style = ParagraphStyle("subtitle", fontSize=11, fontName="Helvetica",
                                 spaceAfter=20, textColor=colors.HexColor("#666666"))
section_style = ParagraphStyle("section", fontSize=14, fontName="Helvetica-Bold",
                                spaceAfter=10, textColor=colors.HexColor("#1a1a2e"),
                                spaceBefore=16, keepWithNext=1)
ticker_style = ParagraphStyle("ticker", fontSize=12, fontName="Helvetica-Bold",
                               spaceAfter=4, textColor=colors.HexColor("#1a1a2e"),
                               keepWithNext=1)
body_style = ParagraphStyle("body", fontSize=9, fontName="Helvetica",
                             spaceAfter=8, textColor=colors.HexColor("#333333"),
                             leading=14)

elements = []

# Title and subtitle
elements.append(Paragraph("Daily Stock Mover Report", title_style))
elements.append(Paragraph(f"Generated on {today}  |  Top 10 & Bottom 10 S&P 500 Movers", subtitle_style))

# Summary table
table_data = [["Ticker", "Company", "% Change", "Category"]]
for ticker in top10.index:
    table_data.append([ticker, company_names.get(ticker, ticker), f"+{top10[ticker]:.2f}%", "Top Performer"])
for ticker in bottom10.index:
    table_data.append([ticker, company_names.get(ticker, ticker), f"{bottom10[ticker]:.2f}%", "Bottom Performer"])

table = Table(table_data, colWidths=[0.8*inch, 2.5*inch, 1*inch, 1.5*inch])
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f9f9f9"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
elements.append(table)
elements.append(Spacer(1, 0.2*inch))

# Stock sections
def add_stock_section(ticker, change, category):
    sign = "+" if change > 0 else ""
    color_hex = "#2e7d32" if change > 0 else "#c62828"
    name = company_names.get(ticker, ticker)
    elements.append(Paragraph(
        f'<font color="{color_hex}">▲</font> {ticker} — {name}  <font color="{color_hex}">{sign}{change:.2f}%</font>  <font color="#888888">— {category}</font>',
        ticker_style))
    chart_path = f"charts/{ticker}.png"
    if os.path.exists(chart_path):
        elements.append(Image(chart_path, width=5*inch, height=2.5*inch))
    elements.append(Paragraph(commentaries[ticker], body_style))
    elements.append(Spacer(1, 0.1*inch))

elements.append(Paragraph("Top Performers", section_style))
for ticker in top10.index:
    add_stock_section(ticker, top10[ticker], "Top Performer")

elements.append(Paragraph("Bottom Performers", section_style))
for ticker in bottom10.index:
    add_stock_section(ticker, bottom10[ticker], "Bottom Performer")

doc.build(elements)
print(f"\nReport saved as: {filename}")
print("Done!")