from types import SimpleNamespace
from unittest.mock import patch

import MetaTrader5 as mt5

from mt5api.server import app


def _symbol_info(*, trade_calc_mode=4):
    return SimpleNamespace(
        visible=True,
        trade_calc_mode=trade_calc_mode,
        volume_min=0.01,
        volume_max=10.0,
        volume_step=0.01,
        trade_contract_size=100.0,
        trade_tick_size=0.01,
        trade_tick_value=1.0,
    )


def test_margin_preview_calculates_effective_buy_and_sell_rates_without_order():
    info = _symbol_info()
    tick = SimpleNamespace(ask=4600.34, bid=4599.96)
    account = SimpleNamespace(currency="USD", leverage=100)

    def calculate(order_type, symbol, volume, price):
        assert symbol == "XAUUSD.p"
        assert volume == 1.0
        if order_type == mt5.ORDER_TYPE_BUY:
            assert price == tick.ask
            return 4600.34
        assert order_type == mt5.ORDER_TYPE_SELL
        assert price == tick.bid
        return 4599.96

    with (
        patch("mt5api.handlers.symbols.ensure_initialized", return_value=True),
        patch("mt5api.handlers.symbols.ensure_symbol", return_value=True),
        patch("mt5api.handlers.symbols.mt5.symbol_info", return_value=info),
        patch("mt5api.handlers.symbols.mt5.symbol_info_tick", return_value=tick),
        patch("mt5api.handlers.symbols.mt5.account_info", return_value=account),
        patch("mt5api.handlers.symbols.mt5.order_calc_margin", side_effect=calculate),
        patch("mt5api.handlers.symbols.mt5.order_send") as order_send,
    ):
        response = app.test_client().get("/symbols/XAUUSD.p/margin?volume=1")

    assert response.status_code == 200
    assert response.get_json() == {
        "account_currency": "USD",
        "account_leverage": 100,
        "buy": {
            "effective_margin_rate": 0.0001,
            "margin": 4600.34,
            "price": 4600.34,
        },
        "sell": {
            "effective_margin_rate": 0.0001,
            "margin": 4599.96,
            "price": 4599.96,
        },
        "symbol": "XAUUSD.p",
        "trade_calc_mode": 4,
        "trade_contract_size": 100.0,
        "trade_tick_size": 0.01,
        "trade_tick_value": 1.0,
        "volume": 1.0,
    }
    order_send.assert_not_called()


def test_margin_preview_rejects_unaligned_volume():
    with (
        patch("mt5api.handlers.symbols.ensure_initialized", return_value=True),
        patch("mt5api.handlers.symbols.ensure_symbol", return_value=True),
        patch("mt5api.handlers.symbols.mt5.symbol_info", return_value=_symbol_info()),
        patch(
            "mt5api.handlers.symbols.mt5.symbol_info_tick",
            return_value=SimpleNamespace(ask=4600.34, bid=4599.96),
        ),
        patch(
            "mt5api.handlers.symbols.mt5.account_info",
            return_value=SimpleNamespace(currency="USD", leverage=100),
        ),
        patch("mt5api.handlers.symbols.mt5.order_calc_margin") as calculate,
    ):
        response = app.test_client().get("/symbols/XAUUSD.p/margin?volume=0.015")

    assert response.status_code == 400
    assert response.get_json() == {"error": "volume is not aligned to symbol volume_step"}
    calculate.assert_not_called()


def test_margin_preview_rejects_non_cfd_index_symbol():
    with (
        patch("mt5api.handlers.symbols.ensure_initialized", return_value=True),
        patch("mt5api.handlers.symbols.ensure_symbol", return_value=True),
        patch(
            "mt5api.handlers.symbols.mt5.symbol_info",
            return_value=_symbol_info(trade_calc_mode=2),
        ),
        patch(
            "mt5api.handlers.symbols.mt5.symbol_info_tick",
            return_value=SimpleNamespace(ask=943.14, bid=942.82),
        ),
        patch(
            "mt5api.handlers.symbols.mt5.account_info",
            return_value=SimpleNamespace(currency="USD", leverage=100),
        ),
        patch("mt5api.handlers.symbols.mt5.order_calc_margin") as calculate,
    ):
        response = app.test_client().get("/symbols/GAUCNH.p/margin")

    assert response.status_code == 422
    assert response.get_json() == {
        "error": "margin preview currently supports trade_calc_mode=4 only"
    }
    calculate.assert_not_called()
