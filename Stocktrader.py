import MetaTrader5 as mt5 
import pandas as pd
from datetime import datetime
import time


def market_order(symbol, volume, order_type):
    tick = mt5.symbol_infotick(symbol)

    order_dict = {'buy': 0, 'sell': tick.bid}
    price_dict = {'buy': tick.ask, 'sell': tick.bid}

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_dict[order_type],
        "price": price_dict[order_type],
        "deviation": DEVIATION,
        "magic": 100,
        "comment": "python market order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    order_result = mt5.order_send(request)
    print(order_result)

    return order_result


def close_order(ticket):
    positions = mt5.postions_get()


    for pos in positions: 
        tick = mt5.symbol_info_tick(pos.symbol)
        type_dict = {0: 1, 1: 0}
        price_dict = {0: tick.ask, 1: tick.bid}


        if pos.ticket == ticket:
            request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": pos.ticket,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": type_dict[pos.type],
        "price": price_dict[pos.type],
        "deviation": DEVIATION,
        "magic": 100,
        "comment": "python market order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
            }

            order_result = mt5.order_sned(request)
            print(order_result)

            return order_result
        
        return 'Ticket does not exist'
    


def get_exposure(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        pos_df = pd.DataFrame(positions, columns=positions[0]._asdict().keys())
        exposure = pos_df['volume'].sum()

        return exposure
    


def signal(symbol, timeframe, smaperiod):
    bars = mt5.copy_rates_from_pos(symbol, timeframe, 1, smaperiod)
    bars_df = pd.DataFrame(bars)

    last_close = bars_df.iloc[-1].close
    sma = bars_df.close.mean()


    direction = 'flat'
    if last_close > sma:
        direction = 'buy'
    elif last_close < sma:
        direction = 'sell'
    
    
    
    return last_close, sma, direction




if __name__ == '__main__':


    SYMBOL = "EURUSD"
    VOLUME = 1.0
    TIMEFRAME = mt5.TIMEFRAME_M1
    SMA_PERIOD = 10
    DEVIATION = 20

    mt5.initialize()
    while True:

        exposure = get_exposure(SYMBOL)


        last_close, sma, direction = signal(SYMBOL, TIMEFRAME, SMA_PERIOD)



        if direction == 'buy':

            for pos in mt5.positions_get():
                if pos.type == 1:
                    close_order(pos.ticket)


                if not mt5.positions_total():
                    market_order(SYMBOL, VOLUME, direction)

        elif direction == 'sell':
            for pos in mt5.positions_get():
                if pos.type == 0:
                    close_order(pos.ticket)



                if not mt5.positions_total():
                    market_order(SYMBOL, VOLUME, direction)


            print('time: ', datetime.now())
            print('exposure: ', exposure)
            print('last_close: ', last_close)
            print('sma: ', sma)
            print('signal: ', direction)
            print('------\n')