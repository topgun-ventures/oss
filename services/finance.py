import numpy as np


def calc_avg(df, price_column, window_span):
    df["SMA"] = df[price_column].rolling(window=window_span).mean()
    df["EWM"] = df[price_column].ewm(span=window_span).mean()
    df["VWAP"] = (df.volume * df[price_column]).cumsum() / df.volume.cumsum()
    df["MIN"] = df[price_column].min()
    df["MAX"] = df[price_column].max()

    return df


def rsi(series, period):
    delta = series.diff().dropna()
    u = delta * 0
    d = u.copy()
    u[delta > 0] = delta[delta > 0]
    d[delta < 0] = -delta[delta < 0]
    u[u.index[period - 1]] = np.mean(u[:period])  # first value is sum of avg gains
    u = u.drop(u.index[: (period - 1)])
    d[d.index[period - 1]] = np.mean(d[:period])  # first value is sum of avg losses
    d = d.drop(d.index[: (period - 1)])
    rs = (
        u.ewm(com=period - 1, adjust=False).mean()
        / d.ewm(com=period - 1, adjust=False).mean()
    )
    return 100 - 100 / (1 + rs)
