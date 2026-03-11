from src.market.hub import MarketDataHub
from src.market.okx_ws import OkxPublicWsClient


def test_okx_ws_client_parses_trade_message_into_hub():
    hub = MarketDataHub()
    client = OkxPublicWsClient(hub, symbol='BTC-USDT-SWAP')
    msg = '{"arg":{"channel":"trades","instId":"BTC-USDT-SWAP"},"data":[{"ts":"1773219000000","px":"70000","sz":"0.5","side":"buy"}]}'
    client.handle_message(msg)
    snap = hub.snapshot('BTC-USDT-SWAP')
    assert len(snap.recent_trades) == 1
    assert snap.recent_trades[0].price == 70000.0


def test_okx_ws_client_parses_bbo_message_into_hub():
    hub = MarketDataHub()
    client = OkxPublicWsClient(hub, symbol='BTC-USDT-SWAP')
    msg = '{"arg":{"channel":"bbo-tbt","instId":"BTC-USDT-SWAP"},"data":[{"ts":"1773219000000","bids":[["69999","2",0,0]],"asks":[["70001","3",0,0]]}]}'
    client.handle_message(msg)
    snap = hub.snapshot('BTC-USDT-SWAP')
    assert snap.top is not None
    assert snap.top.bid_price == 69999.0
    assert snap.top.ask_price == 70001.0
