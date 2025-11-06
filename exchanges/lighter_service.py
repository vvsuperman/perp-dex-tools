import asyncio
import json
import signal
import logging
import os
import sys
import time
import requests
import argparse
import traceback
import csv
from decimal import Decimal
from typing import Tuple, List, Dict, Any


from lighter.signer_client import SignerClient
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from keys import BASE_URL
import random
from .base import BaseExchangeClient, OrderResult, OrderInfo, query_retry
import lighter
from lighter import SignerClient, ApiClient, Configuration
logger = logging.getLogger(f"lighter_hedge_bot")
logger.setLevel(logging.INFO)
logger.handlers.clear()

logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('websockets').setLevel(logging.WARNING)
# 在日志配置部分，替换你原来的 lighter 设置
logging.getLogger('lighter').disabled = True


file_handler = logging.FileHandler('logs/lighter_hedge_bot.log')
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')

file_handler.setFormatter(file_formatter)
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.propagate = False

# ========================================
# Lighter_Service 类（无锁、无 abs）
# ========================================
class Lighter_Service:
    def __init__(self, config: dict):
        self.id = config["id"]
        self.account_index = config["LIGHTER_ACCOUNT_INDEX"]
        self.api_key_private_key = config.get("API_KEY_PRIVATE_KEY")
        self.api_key_index = config["LIGHTER_API_KEY_INDEX"]
        self.ticker_marketId = {}
        self.api_client = ApiClient(configuration=Configuration(host=BASE_URL))
        self.lighter_client = None

    def initial_client(self):

        if self.lighter_client is None:
            self.lighter_client = lighter.SignerClient(
                url=BASE_URL,
                private_key=self.api_key_private_key,
                account_index=self.account_index,
                api_key_index=self.api_key_index,
            )
            return 
        else:
            try:
                err = self.lighter_client.check_client()
                if err is not None:
                    logger.info(f"CheckClient error: {err}")
                    self.lighter_client = lighter.SignerClient(
                        url=BASE_URL,
                        private_key=self.api_key_private_key,
                        account_index=self.account_index,
                        api_key_index=self.api_key_index,
                    )
                return 
            except Exception as e:
                logger.info(f"CheckClient exception: {e}", "ERROR")
                self.lighter_client = lighter.SignerClient(
                    url=BASE_URL,
                    private_key=self.api_key_private_key,
                    account_index=self.account_index,
                    api_key_index=self.api_key_index,
                )
                return

    async def close_all_positions(self) -> None:
        positions = await self.get_account_positions()
        for position in positions:
            qty = Decimal(position.position)
            if qty != 0:  # 非零持仓
                side = "sell" if position.sign == 1 else "buy"
                await self.place_market_order(position.symbol, qty, side)

    async def cancel_all_active_orders(self) -> None:
        logger.info(f"开始取消账户{self.id} - {self.account_index} 的所有活跃订单...")
        try:
            positions = await self.get_account_positions()
            symbols = {
                p.symbol for p in positions
                if Decimal(p.position) > 0  # 直接判断非零
            } if positions else set()

            # self.initial_client()
            for symbol in symbols:
                try:
                    market_info = await self.get_market_info(symbol)
                    market_index = market_info["market_index"]
                    active_orders = await self.fetch_active_orders_with_retry(symbol)
                  
                    if not active_orders:
                        continue
                    for order in active_orders:
                        tx = await self.lighter_client.cancel_order(
                            market_index=market_index,
                            order_index=order.client_order_index
                        )
                        logger.info(f"取消成功: {symbol} | {order.client_order_index} | tx={tx}")
                        await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(f"账户 {self.account_index}取消失败 {symbol}: {e}")
            logger.info(f"账户 {self.id}-{self.account_index} 订单取消完成")
        except Exception as e:
            logger.error(f"账户 {self.account_index}取消订单异常: {e}")
            logger.error(traceback.format_exc())

    async def get_balance(self):
        account = await self.get_account_with_retry()
        return Decimal(account.available_balance)

    @query_retry(reraise=True)
    async def get_account_with_retry(self) -> Any:
        account_api = lighter.AccountApi(self.api_client)
        account_data = await account_api.account(by="index", value=str(self.account_index))
        if not account_data or not account_data.accounts:
            raise ValueError("Failed to get positions")
        return account_data.accounts[0]

    async def get_account_positions(self):
        account = await self.get_account_with_retry()
        return account.positions
    @query_retry(reraise=True)
    def get_lighter_market_config(self, symbol) -> Tuple[int, int, int]:
        try:
            url = f"{BASE_URL}/api/v1/orderBooks"
            response = requests.get(url, headers={"accept": "application/json"}, timeout=20)
            response.raise_for_status()
            data = response.json()
            for market in data["order_books"]:
                if market["symbol"] == symbol:
                    return (
                        market["market_id"],
                        pow(10, market["supported_size_decimals"]),
                        pow(10, market["supported_price_decimals"])
                    )
            raise Exception(f"symbol {symbol} not found")
        except Exception as e:
            logger.info(f" Error fetching market info for {symbol}: {e}")
            raise e

    async def get_market_info(self, symbol: str):
        if symbol not in self.ticker_marketId:
            market_index, size_dec, price_dec = self.get_lighter_market_config(symbol)
            self.ticker_marketId[symbol] = {
                'market_index': market_index,
                'supported_size_decimals': size_dec,
                'supported_price_decimals': price_dec
            }
        return self.ticker_marketId[symbol]

    async def get_price(self, symbol: str = ""):
       
        market_info = await self.get_market_info(symbol)
        market_index = market_info.get('market_index')
        order_api = lighter.OrderApi(self.api_client)
        order_book = await order_api.order_book_orders(market_id=market_index, limit=3)
        best_bid = Decimal(order_book.bids[0].price)
        best_ask = Decimal(order_book.asks[0].price)
        return (best_bid + best_ask) / Decimal('2')


    @query_retry(reraise=True)
    async def get_inactive_orders(self):   
        try:   
            self.initial_client()
            auth_token, error = self.lighter_client.create_auth_token_with_expiry()
            if error:
                raise ValueError(f"Auth error: {error}")
            order_api = lighter.OrderApi(self.api_client)
            resp = await order_api.account_inactive_orders(
                account_index=self.account_index,
                limit=10,
                auth=auth_token
            )
        
            if resp.code != 200:
                raise Exception("get active orders failed",)
            else:
                resp.orders
        except Exception as e:
            logger.error(f"获取inactive orders异常:",e)

    @query_retry(reraise=True)
    async def fetch_active_orders_with_retry(self, symbol) -> List[Dict[str, Any]]:
       
        self.initial_client()
        market_index = (await self.get_market_info(symbol))['market_index']
        auth_token, error = self.lighter_client.create_auth_token_with_expiry()
        if error:
            raise ValueError(f"Auth error: {error}")
        order_api = lighter.OrderApi(self.api_client)
        resp = await order_api.account_active_orders(
            account_index=self.account_index,
            market_id=market_index,
            auth=auth_token
        )
    
        if resp.code != 200:
            raise Exception("get active orders failed",)
        else:
            return resp.orders

    async def place_market_order(self, symbol: str, quantity: Decimal, direction: str,
                                         price: Decimal = 0):
        logger.info(f"Placing market order for {self.id} {symbol} {direction} {quantity}" )
        try:
            market_info = await self.get_market_info(symbol)
            market_index = market_info['market_index']
            base_mul = market_info['supported_size_decimals']
            price_mul = market_info['supported_price_decimals']

            if price == 0:
                price = await self.get_price(symbol)

            if direction == 'buy':
                is_ask = False
                exec_price = price * Decimal('1.02')
                
            else:
                is_ask = True
                exec_price = price * Decimal('0.98')
 
            main_id = int(time.time() * 1000)

        
            self.initial_client()

            tx = await self.lighter_client.create_order(
                market_index=market_index,
                client_order_index=main_id,
                base_amount=int(quantity * base_mul),
                price=int(exec_price * price_mul),
                is_ask=is_ask,
                order_type=self.lighter_client.ORDER_TYPE_LIMIT,
                time_in_force=self.lighter_client.ORDER_TIME_IN_FORCE_GOOD_TILL_TIME,
                reduce_only=False,
                trigger_price=0,
                order_expiry=self.lighter_client.DEFAULT_28_DAY_ORDER_EXPIRY
            )
            logger.info(f"下单成功: tx={tx}")
            
            return main_id

            

            # await self.lighter_client.close()
        except Exception as e:
            logger.error(f"market订单下单失败: {e}")

    async def place_sl_tp_order(self, symbol: str, quantity: Decimal, direction: str,
                                price: Decimal=0, sl_percent: Decimal = 0, tp_percent: Decimal = 0):
        try:
            logger.info(f"Placing sl-tp order for {self.id} {symbol} direction {direction} quantity {quantity} sl_percent {sl_percent} tp_percent:{tp_percent}" )


            self.initial_client()
        
            market_info = await self.get_market_info(symbol)
            market_index = market_info['market_index']
            base_mul = market_info['supported_size_decimals']
            price_mul = market_info['supported_price_decimals']

            
            if price == 0:
                    price = await self.get_price(symbol)

            if direction == 'buy':
                is_ask = False
               
                sl_price = price * Decimal(1 - sl_percent)
                tp_price = price * Decimal(1 + tp_percent)
            else:
                is_ask = True
                sl_price = price * Decimal(1 + sl_percent)
                tp_price = price * Decimal(1 - tp_percent)
                

            if sl_percent > 0:
                    sl_id =  int(time.time() * 1000)
                    tx = await self.lighter_client.create_sl_order(
                        market_index=market_index,
                        client_order_index=sl_id,
                        base_amount=int(quantity * base_mul),
                        trigger_price=int(sl_price * price_mul),
                        price=int(sl_price * price_mul),
                        is_ask =not is_ask
                    )
                    logger.info(f"SL单成功: tx={tx}")

            await asyncio.sleep(1)

            if tp_percent > 0:
                tp_id =  int(time.time() * 1000)
                tx = await self.lighter_client.create_tp_order(
                    market_index=market_index,
                    client_order_index=tp_id,
                    base_amount=int(quantity * base_mul),
                    trigger_price=int(tp_price * price_mul),
                    price=int(tp_price * price_mul),
                    is_ask=not is_ask
                )
                logger.info(f"TP单成功: tx={tx}")
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"sl tp单失败: {e}")

    async def cancel_order(self, symbol: str, order_id: str) -> OrderResult:
        await self.initial_client()
        market_index = (await self.get_market_info(symbol))["market_index"]
        success, tx_hash, error = await self.lighter_client.cancel_order(
            market_index=market_index,
            order_index=int(order_id)
        )
        return (True, tx_hash) if success else (False, error or "Cancel failed")

    def round_to_tick(self, num, decimals) -> Decimal:
        return Decimal(num).quantize(decimals)