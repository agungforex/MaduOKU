from unittest.mock import MagicMock, patch

import pytest

from maduoku.data import binance_futures

_SAMPLE_KLINE = [
    1700000000000, "100.0", "105.0", "95.0", "102.0", "10.5",
    1700003599999, "1071.0", 42, "5.0", "510.0", "0",
]


def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


@patch("maduoku.data.binance_futures.requests.get")
def test_fetch_ohlcv_parses_klines(mock_get):
    mock_get.return_value = _mock_response([_SAMPLE_KLINE, _SAMPLE_KLINE])

    df = binance_futures.fetch_ohlcv("BTCUSDT", interval="1h", limit=2)

    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(df) == 2
    assert df["Close"].iloc[0] == pytest.approx(102.0)

    called_params = mock_get.call_args.kwargs["params"]
    assert called_params["symbol"] == "BTCUSDT"
    assert called_params["interval"] == "1h"
    assert called_params["limit"] == 2


@patch("maduoku.data.binance_futures.requests.get")
def test_fetch_ohlcv_raises_on_empty_response(mock_get):
    mock_get.return_value = _mock_response([])

    with pytest.raises(ValueError):
        binance_futures.fetch_ohlcv("BTCUSDT")


@patch("maduoku.data.binance_futures.requests.get")
def test_fetch_ohlcv_caps_limit_at_1500(mock_get):
    mock_get.return_value = _mock_response([_SAMPLE_KLINE])

    binance_futures.fetch_ohlcv("BTCUSDT", limit=5000)

    assert mock_get.call_args.kwargs["params"]["limit"] == 1500
