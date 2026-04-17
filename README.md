# Daily S&P 500 Market Mover Report

An automated Python script that generates a daily institutional-style market report for the S&P 500.

## What it does
- Pulls live price and volume data for all 500 S&P 500 stocks
- Identifies the top 10 and bottom 10 movers of the day
- Generates 30-day price charts for each stock
- Uses the Anthropic API to write professional analyst commentary based on price and volume signals
- Outputs everything into a clean, formatted PDF report

## Libraries used
yfinance, pandas, matplotlib, reportlab, anthropic, requests

## Setup
1. Install dependencies: `pip install yfinance pandas matplotlib reportlab anthropic requests`
2. Add your Anthropic API key to the `API_KEY` variable
3. Run: `python sp500_mover_report.py`
