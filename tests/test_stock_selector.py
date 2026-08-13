candidates = [
    {
        "symbol": "AAPL",
        "return_30d": 8.5,
        "volatility": 25.3,
        "volume_ratio": 1.8,
        "rsi": 58.2
    },
    {
        "symbol": "NVDA",
        "return_30d": 15.2,
        "volatility": 42.1,
        "volume_ratio": 2.4,
        "rsi": 67.5
    },
    {
        "symbol": "MSFT",
        "return_30d": 4.1,
        "volatility": 20.2,
        "volume_ratio": 1.1,
        "rsi": 52.4
    }
]

selector = StockSelector(api_key)

selected = selector.select_stocks(
    candidates=candidates,
    market_data="미국 증시는 최근 상승 추세",
    top_n=2
)

print(selected)