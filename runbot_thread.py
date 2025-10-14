#!/usr/bin/env python3
"""
Modular Trading Bot - Supports multiple exchanges
"""

import argparse
import asyncio
import logging
from pathlib import Path
import sys
import dotenv
from decimal import Decimal
from trading_bot import TradingBot, TradingConfig
from exchanges import ExchangeFactory
from keys import Keys
import multiprocessing
import time


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Modular Trading Bot - Supports multiple exchanges')

    # Exchange selection
    parser.add_argument('--exchange', type=str, default='edgex',
                        choices=ExchangeFactory.get_supported_exchanges(),
                        help='Exchange to use (default: edgex). '
                             f'Available: {", ".join(ExchangeFactory.get_supported_exchanges())}')

    # Trading parameters
    parser.add_argument('--ticker', type=str, default='ETH',
                        help='Ticker (default: ETH)')
    parser.add_argument('--quantity', type=Decimal, default=Decimal(0.1),
                        help='Order quantity (default: 0.1)')
    parser.add_argument('--take-profit', type=Decimal, default=Decimal(0.02),
                        help='Take profit in USDT (default: 0.02)')
    parser.add_argument('--direction', type=str, default='buy', choices=['buy', 'sell'],
                        help='Direction of the bot (default: buy)')
    parser.add_argument('--max-orders', type=int, default=40,
                        help='Maximum number of active orders (default: 40)')
    parser.add_argument('--wait-time', type=int, default=450,
                        help='Wait time between orders in seconds (default: 450)')
    parser.add_argument('--env-file', type=str, default=".env",
                        help=".env file path (default: .env)")
    parser.add_argument('--grid-step', type=str, default='-100',
                        help='The minimum distance in percentage to the next close order price (default: -100)')
    parser.add_argument('--stop-price', type=Decimal, default=-1,
                        help='Price to stop trading and exit. Buy: exits if price >= stop-price.'
                        'Sell: exits if price <= stop-price. (default: -1, no stop)')
    parser.add_argument('--pause-price', type=Decimal, default=-1,
                        help='Pause trading and wait. Buy: pause if price >= pause-price.'
                        'Sell: pause if price <= pause-price. (default: -1, no pause)')
    parser.add_argument('--boost', action='store_true',
                        help='Use the Boost mode for volume boosting')

    return parser.parse_args()


def setup_logging(log_level: str):
    """Setup global logging configuration."""
    # Convert string level to logging constant
    level = getattr(logging, log_level.upper(), logging.DEBUG)

    # Clear any existing handlers to prevent duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure root logger WITHOUT adding a console handler
    # This prevents duplicate logs when TradingLogger adds its own console handler
    root_logger.setLevel(level)

    # Suppress websockets debug logs unless DEBUG level is explicitly requested
    if log_level.upper() != 'DEBUG':
        logging.getLogger('websockets').setLevel(logging.WARNING)

    # Suppress other noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    # Suppress Lighter SDK debug logs
    logging.getLogger('lighter').setLevel(logging.DEBUG)
    # Also suppress any root logger DEBUG messages that might be coming from Lighter
    if log_level.upper() != 'DEBUG':
        # Set root logger to WARNING to suppress DEBUG messages from Lighter SDK
        root_logger.setLevel(logging.WARNING)


async def main():
    """Main entry point."""
    args = parse_arguments()

    # Setup logging first
    setup_logging("WARNING")
    processes = []

    # List to store (process, config) pairs
    process_config_pairs = []
    max_restarts = 5  # Limit restarts per process
    restart_counts = {}  # Track restart attempts per process index
    
    for key in Keys:
    
        config = TradingConfig(
            ticker=key.get('ticker').upper(),
            contract_id='',  # will be set in the bot's run method
            tick_size=Decimal(0),
            quantity=key.get('quantity'),
            take_profit=Decimal(key.get('take_profit')),
            direction=key.get('direction').lower(),
            max_orders=key.get('max_orders'),
            wait_time=key.get('wait_time'),
            exchange=key.get('exchange').lower(),
            grid_step=Decimal(key.get('grid_step')),
            stop_price=Decimal(key.get('stop_price',-1)),
            pause_price=Decimal(key.get('pause_price',-1)),
            API_KEY_PRIVATE_KEY = key.get('API_KEY_PRIVATE_KEY'),
            API_KEY_PUBLIC_KEY = key.get('API_KEY_PUBLIC_KEY'),
            LIGHTER_ACCOUNT_INDEX = key.get('LIGHTER_ACCOUNT_INDEX'),
            LIGHTER_API_KEY_INDEX = key.get('LIGHTER_API_KEY_INDEX'),
            BACKPACK_PUBLIC_KEY = key.get('BACKPACK_PUBLIC_KEY'),
            BACKPACK_SECRET_KEY = key.get('BACKPACK_SECRET_KEY'),
            EXTENDED_VAULT = key.get('EXTENDED_VAULT'),
            EXTENDED_STARK_KEY_PRIVATE = key.get('EXTENDED_STARK_KEY_PRIVATE'),
            EXTENDED_STARK_KEY_PUBLIC = key.get('EXTENDED_STARK_KEY_PUBLIC'),
            EXTENDED_API_KEY = key.get('EXTENDED_API_KEY'),
            GRVT_TRADING_ACCOUNT_ID = key.get('GRVT_TRADING_ACCOUNT_ID'),
            GRVT_API_KEY = key.get('GRVT_API_KEY'),
            GRVT_PRIVATE_KEY = key.get('GRVT_PRIVATE_KEY'),
            PARADEX_L1_ADDRESS = key.get('PARADEX_L1_ADDRESS'),
            PARADEX_L2_ADDRESS = key.get('PARADEX_L2_ADDRESS'),
            PARADEX_L2_PRIVATE_KEY = key.get('PARADEX_L2_PRIVATE_KEY'),
            boost_mode=False
        )
       
        # Create and run the bot
     
        try:
            p = multiprocessing.Process(target=run_async_function, 
                                    args=(config,))
            # Store process and config as a tuple
            process_config_pairs.append((p, config))
            restart_counts[len(process_config_pairs) - 1] = 0  # Initialize restart count
            p.start()
            time.sleep(10)
        except Exception as e:
            print(f"Bot execution failed for {config.ticker}: {e}")
            return

        print(f"All processes started. Total: {len(process_config_pairs)}")

    try:
        while True:
            alive_count = sum(1 for p, _ in process_config_pairs if p.is_alive())
            print(f"Active workers: {alive_count}/{len(process_config_pairs)}")
            
            # Check for dead processes and restart them
            for i, (p, config) in enumerate(process_config_pairs):
                if not p.is_alive():
                    print(f"Process {i} for {config.ticker} died, exit code: {p.exitcode}")
                    if restart_counts.get(i, 0) < max_restarts:
                        print(f"Restarting process {i} for {config.ticker}...")
                        p.join()  # Clean up the dead process
                        new_process = multiprocessing.Process(target=run_async_function, 
                                                            args=(config,))
                        process_config_pairs[i] = (new_process, config)  # Update with new process
                        restart_counts[i] = restart_counts.get(i, 0) + 1
                        new_process.start()
                    else:
                        print(f"Process {i} for {config.ticker} reached max restarts ({max_restarts}). Not restarting.")

            time.sleep(600)
   
    
    except KeyboardInterrupt:
        print("Shutting down all processes...")
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join()

def run_async_function(config):
    """在子进程中运行异步函数的辅助函数"""
    asyncio.run(TradingBot(config).run())

if __name__ == "__main__":
    asyncio.run(main())
