import MetaTrader5 as mt5 
import pandas as pd
from datetime import datetime
import time
import logging
import os
from pathlib import Path
import json

def setup_logging():
   
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = log_dir / f"trading_{current_time}.log"
    
    
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
   
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
   
    trade_data_file = log_dir / f"trade_data_{current_time}.csv"
    return trade_data_file

def log_trade_data(trade_data_file, data_dict):
    """Log  the trade data to CSV file"""
    df = pd.DataFrame([data_dict])
    if not trade_data_file.exists():
        df.to_csv(trade_data_file, mode='w', header=True, index=False)
    else:
        df.to_csv(trade_data_file, mode='a', header=False, index=False)

def market_order(symbol, volume, order_type):
    try:
        tick = mt5.symbol_info_tick(symbol)
        
        order_dict = {'buy': 0, 'sell': 1}
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
        
        logging.info(f"Sending order request: {json.dumps(request, indent=2)}")
        
        order_result = mt5.order_send(request)
        
        if order_result.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"Order executed successfully: {order_result}")
            logging.info(f"Opened {order_type} position: Volume={volume}, Price={order_result.price}")
        else:
            logging.error(f"Order failed. Error code: {order_result.retcode}")
            logging.error(f"Error description: {mt5.last_error()}")
        
        return order_result
    
    except Exception as e:
        logging.error(f"Error in market_order: {str(e)}")
        return None

def close_order(ticket):
    try:
        positions = mt5.positions_get()
        
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
                    "comment": "python close order",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                logging.info(f"Sending close order request: {json.dumps(request, indent=2)}")
                
                order_result = mt5.order_send(request)
                
                if order_result.retcode == mt5.TRADE_RETCODE_DONE:
                    profit = pos.profit
                    logging.info(f"Position closed successfully: Ticket={ticket}, Profit={profit}")
                else:
                    logging.error(f"Close order failed. Error code: {order_result.retcode}")
                    logging.error(f"Error description: {mt5.last_error()}")
                
                return order_result
            
        logging.warning(f"Ticket {ticket} does not exist")
        return 'Ticket does not exist'
        
    except Exception as e:
        logging.error(f"Error in close_order: {str(e)}")
        return None

def log_account_info():
    try:
        account_info = mt5.account_info()
        if account_info is not None:
            logging.info(f"""
            Account Information:
            Balance: {account_info.balance}
            Equity: {account_info.equity}
            Profit: {account_info.profit}
            Margin Level: {account_info.margin_level}%
            """)
        else:
            logging.error("Failed to get account info")
    except Exception as e:
        logging.error(f"Error getting account info: {str(e)}")

def get_exposure(symbol):
   
    try:
        positions = mt5.positions_get(symbol=symbol)
        if positions:
            pos_df = pd.DataFrame(positions, columns=positions[0]._asdict().keys())
            exposure = pos_df['volume'].sum()
            
            logging.info(f"Current {symbol} exposure: {exposure}")
            
            for pos in positions:
                logging.debug(f"""
                Position Details:
                Ticket: {pos.ticket}
                Type: {'Buy' if pos.type == 0 else 'Sell'}
                Volume: {pos.volume}
                Price: {pos.price_open}
                Profit: {pos.profit}
                """)
            
            return exposure
        else:
            logging.info(f"No open positions for {symbol}")
            return 0
            
    except Exception as e:
        logging.error(f"Error in get_exposure for {symbol}: {str(e)}")
        return 0

def signal(symbol, timeframe, smaperiod):
   
    try:
        bars = mt5.copy_rates_from_pos(symbol, timeframe, 1, smaperiod)
        if bars is None:
            logging.error(f"Failed to get historical data for {symbol}")
            return None, None, 'flat'
            
        bars_df = pd.DataFrame(bars)
        
        last_close = bars_df.iloc[-1].close
        sma = bars_df.close.mean()
        
        direction = 'flat'
        if last_close > sma:
            direction = 'buy'
        elif last_close < sma:
            direction = 'sell'
        
        logging.info(f"""
        Signal Analysis:
        Symbol: {symbol}
        Timeframe: {timeframe}
        Last Close: {last_close:.5f}
        SMA({smaperiod}): {sma:.5f}
        Direction: {direction}
        Price-SMA Distance: {(last_close - sma):.5f}
        """)
        
        return last_close, sma, direction
        
    except Exception as e:
        logging.error(f"Error in signal generation for {symbol}: {str(e)}")
        return None, None, 'flat'

def log_market_conditions(symbol):
    """Log current market conditions"""
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is not None:
            logging.info(f"""
            Market Conditions for {symbol}:
            Bid: {tick.bid}
            Ask: {tick.ask}
            Spread: {tick.ask - tick.bid}
            Last: {tick.last}
            Volume: {tick.volume}
            Time: {datetime.fromtimestamp(tick.time)}
            """)
    except Exception as e:
        logging.error(f"Error logging market conditions: {str(e)}")

if __name__ == '__main__':
    SYMBOL = "EURUSD"
    VOLUME = 1.0
    TIMEFRAME = mt5.TIMEFRAME_M1
    SMA_PERIOD = 10
    DEVIATION = 20
    
    # Initialize logging and MT5
    trade_data_file = setup_logging()
    logging.info("Starting trading system")
    
    if not mt5.initialize():
        logging.error(f"MT5 initialization failed: {mt5.last_error()}")
        exit()
    
    logging.info("MT5 initialized successfully")
    
    while True:
        try:
            # Log current time and account info every iteration
            current_time = datetime.now()
            log_account_info()
            
            # Get trading data
            exposure = get_exposure(SYMBOL)
            last_close, sma, direction = signal(SYMBOL, TIMEFRAME, SMA_PERIOD)
            
            # Log trade data
            trade_data = {
                'timestamp': current_time,
                'symbol': SYMBOL,
                'exposure': exposure,
                'last_close': last_close,
                'sma': sma,
                'signal': direction,
                'account_balance': mt5.account_info().balance,
                'account_equity': mt5.account_info().equity
            }
            log_trade_data(trade_data_file, trade_data)
            
            # Log current market state
            logging.info(f"""
            Time: {current_time}
            Symbol: {SYMBOL}
            Exposure: {exposure}
            Last Close: {last_close}
            SMA: {sma}
            Signal: {direction}
            """)
            
            # Execute trading logic
            if direction == 'buy':
                for pos in mt5.positions_get():
                    if pos.type == 1:  # Close sell positions
                        close_order(pos.ticket)
                
                if not mt5.positions_total():
                    market_order(SYMBOL, VOLUME, direction)
            
            elif direction == 'sell':
                for pos in mt5.positions_get():
                    if pos.type == 0:  # Close buy positions
                        close_order(pos.ticket)
                
                if not mt5.positions_total():
                    market_order(SYMBOL, VOLUME, direction)
            
            # Add delay to prevent excessive logging
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            time.sleep(5)  # Longer delay on error
