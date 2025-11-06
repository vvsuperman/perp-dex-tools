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

from exchanges.backpack import BackpackClient
import websockets
from datetime import datetime
import pytz
from keys import KEYS, MULTIPLIER_QUANTITY , HEDGE_INTERVAL_SECONDS, HEDGE_SYMBOLS,WEBHOOK_URL,SL,TP,BASE_URL
import random
from exchanges.base import BaseExchangeClient, OrderResult, OrderInfo, query_retry
import lighter
from lighter import SignerClient, ApiClient, Configuration
from monitor.db import Lighter_Dao
from exchanges.lighter_service import Lighter_Service

lighter_dao = Lighter_Dao()



# MULTIPLIER_QUANTITY = 0
# HEDGE_INTERVAL_SECONDS = 0
# HEDGE_SYMBOLS = []
# WEBHOOK_URL=''
# SL = 0
# TP = 0
# keys = []
# ========================================
# 日志配置
# ========================================
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
from pathlib import Path
import dotenv
import importlib.util



def send_webhook_alert(msg: str):
        """Send webhook alert for new token discovery"""
        
        message ={"msgtype": "text", 
         "text": {"content": f"exchange监控消息提醒,lighter异常: {msg}"} }
        
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(WEBHOOK_URL, json=message, headers=headers, timeout=10)

            if response.status_code == 200:
                logging.info(f"Webhook alert sent for ({msg})")
            else:
                logging.info(f"Failed to send webhook: {msg}")
        except Exception as e:
            logging.info(f"Error sending webhook: {e}")




# ========================================
# Hedge_Bot 类
# ========================================
class Hedge_Bot:
    async def trading_loop(self):
       
            logger.info(f"Starting trading loop...")
          
            lighter_service_list: List[Lighter_Service] = []
            for key in KEYS:
                service = Lighter_Service(key)
                lighter_service_list.append(service)
                await asyncio.sleep(5)

            
            while True:
                try:
                # 随机选一个标的
            
                    logger.info("--------------------------------------------------------")
                    logger.info(f"[0] prepare close operation all the srvice  ")
                    balance_service: dict[Decimal, Lighter_Service] ={}
                    service_to_balance: dict[Lighter_Service, Decimal] = {}

                    for service in lighter_service_list:
                        await service.cancel_all_active_orders()
                        await service.close_all_positions()
                        
                    logger.info(f"------- all the service cleared sucess wait for cache to refresh ------")
                    await asyncio.sleep(60)

                    for service in lighter_service_list:
                        balance = await service.get_balance()
                        if balance in balance_service:
                            balance += Decimal(0.01)
                            
                        balance_service[balance] = service
                        service_to_balance[service] = balance

                    # 2. 按 balance 从大到小排序，取出 service 列表
                    sorted_services: List['Lighter_Service'] = [
                        service for balance, service in sorted(balance_service.items(), key=lambda x: x[0], reverse=True)
                    ]

                    # 3. 依次成对取出（从高到低）
                    service_pairs: List[Tuple['Lighter_Service', 'Lighter_Service']] = []
                    for i in range(0, len(sorted_services), 2):
                        if i + 1 < len(sorted_services):
                            service_pairs.append((sorted_services[i], sorted_services[i + 1]))
                        else:
                            # 如果总数是奇数，最后一个 service 无法配对，可选择忽略或单独处理
                            logger.warning(f"Service {sorted_services[i]} has no pair (odd number of services)")
                    logger.info(f"------------ service panel--------------------")
                    logger.info("service 处理对为 " + ", ".join(f"({s.id}, {service_to_balance[s]})" for pair in service_pairs for s in pair))
                    # 4. 现在 service_pairs 就是你想要的“按 balance 排序后成对取出”的结果
                    for idx, (service1, service2) in enumerate(service_pairs):
                       
                        
                        ticker = random.choice(HEDGE_SYMBOLS)
                       
                        balance1 = service_to_balance[service1]
                        balance2 = service_to_balance[service2]
                        id1 = service1.id
                        id2 = service2.id

                        logger.info("-----------------------------------------------")
                        logger.info(f"Trading loop begin..")
                        logger.info("-----------------------------------------------")
                        logger.info(f"[1] account{id1} balance: {balance1} |  account {id2} balance: {balance2}")

                        
                        price = await service1.get_price(symbol=ticker)
                        amount = min(balance1, balance2) * Decimal(MULTIPLIER_QUANTITY) 
                        quantity = amount / price

                        logger.info("-----------------------------------------------")
                        logger.info(f"[2] begin Hedge {id1} {id2}  {ticker}  quantity: {quantity} @ {price}")

                        try:
                            logger.info(f"------------[2.1] market order on {id1} vs {id2}----------")
                            await service1.place_market_order(ticker, quantity, 'buy', price)
                            logger.info(f"------------[2.2] begin Hedge {id1} vs {id2}----------")
                            await service2.place_market_order(ticker, quantity, 'sell', price)
                            logger.info(f"------------[2.3] place {id1} vs {id2} market order finished, wait for cache refresh----------")

                            await asyncio.sleep(10)
                            await service1.place_sl_tp_order(ticker, quantity, 'buy', price, SL, TP)
                            await service2.place_sl_tp_order(ticker, quantity, 'sell', price, SL, TP)
                            asyncio.create_task(lighter_dao.save_position_record(
                                account_id=service1.id,
                                account_index=service1.account_index,
                                ticker=ticker,
                                quantity=float(quantity),
                                amount=float(amount),
                                direction='buy',
                                entry_price = float(price)
                            ))
                            asyncio.create_task(lighter_dao.save_position_record(
                                account_id=service2.id,
                                account_index=service2.account_index,
                                ticker=ticker,
                                quantity=float(quantity),
                                amount=float(amount),
                                direction='sell',
                                entry_price = float(price)
                            ))

                        except Exception as e:
                            logger.error(f"下单失败: {e}")
                            break
                        
                        #处理完一组后随机歇会儿
                        await asyncio.sleep( random.randint(60, 120))

                    # 可能会查询异常，失败等情况
                    logger.info("-----------------订单均已处理完毕， 开始进行持仓检查------------------")
                    itr = 1
                    if itr <= 3:
                        logger.info(f"[3] begin check {id1} {id2}  position and order balance for {itr} times")
                        for idx, (service1, service2) in enumerate(service_pairs):
                                           
                                if not await self.compare_positions_and_orders(service1, service2):
                                    logger.error("对冲失败，清理并继续")
                                    try:
                                        await self.close_orders_positions(service1, service2)
                                    except Exception as e:
                                        logger.error(f"不平衡清理失败: {e}")
                                        send_webhook_alert("lighter对冲失败，不平衡，清理失败")
                        itr+=1
                        asyncio.sleep(60*itr)

                

                except Exception as e:
                    logger.error(f"交易循环异常: {e}")
                    send_webhook_alert(f"lighter对冲交易循环异常: {e}")
                    try:
                        await self.close_orders_positions(service1, service2)
                    except Exception as e:
                        logger.error(f"最总清理仓位失败: {e}")
                        send_webhook_alert("最总清理仓位失败")
                
                logger.info(f"-----------------lighter对冲交易循环完毕--------------")
                # finally:
                #     logger.error(f"交易循环异常,finally处理: {e}")
                #     send_webhook_alert(f"lighter对冲交易循环异常: {e}")
                #     try:
                #         await self.close_orders_positions(service1, service2)
                #     except Exception as e:
                #         logger.error(f"最总清理仓位失败: {e}")
                #         send_webhook_alert("最总清理仓位失败")
                
                await asyncio.sleep(HEDGE_INTERVAL_SECONDS + random.randint(0, int(HEDGE_INTERVAL_SECONDS/2)))
       

    async def close_orders_positions(self, service1, service2):   
        try:
            await service1.cancel_all_active_orders()
            await service2.cancel_all_active_orders()
            await service1.close_all_positions()
            await service2.close_all_positions()
        except Exception as e:
            logger.error(f"close_orders_positions error: {e}")
            raise e    

    async def compare_positions_and_orders(self, service1: Lighter_Service, service2: Lighter_Service) -> bool:
        logger.info(f"=== {service1.id} vs {service2.id}开始对冲一致性校验（持仓 + SL/TP 方向相反）===")
        try:
            pos1 = {
                p.symbol: (Decimal(p.position), p.sign)
                for p in await service1.get_account_positions()
                if Decimal(p.position) != 0  # 非零持仓
            }
            pos2 = {
                p.symbol: (Decimal(p.position), p.sign)
                for p in await service2.get_account_positions()
                if Decimal(p.position) != 0  # 非零持仓
            }
            symbols = set(pos1.keys()) | set(pos2.keys())

            pos_ok = True
            for sym in symbols:
                if sym not in pos1 or sym not in pos2:
                    logger.error(f"持仓缺失: {sym}")
                    pos_ok = False
                    continue
                q1, s1 = pos1[sym]
                q2, s2 = pos2[sym]
                if q1 != q2:
                    logger.error(f"数量不等 [{sym}] {q1} ≠ {q2}")
                    pos_ok = False
                if s1 != -s2:
                    logger.error(f"方向不相反 [{sym}] {s1} vs {s2}")
                    pos_ok = False
            if not pos_ok:
                return False
            logger.info("持仓校验通过")

            # ========================================
            # 2. 获取订单 + 分类 SL/TP
            # ========================================
            orders1 = {}
            orders2 = {}
            for sym in symbols:
               
                orders1[sym] = await service1.fetch_active_orders_with_retry(sym)
                orders2[sym] = await service2.fetch_active_orders_with_retry(sym)

            logger.info(f"{service1.id} orders: {orders1[sym]}")
            logger.info(f"{service2.id} orders: {orders2[sym]}")


            # 提取订单关键信息：(symbol, type, trigger_price, remaining_base_amount, is_ask)
            def extract_order_key(order):
                if not hasattr(order, 'type') or order.type not in ('stop-loss', 'take-profit'):
                    return None
                try:
                    qty = Decimal(order.remaining_base_amount)
                    price = Decimal(order.trigger_price)
                    is_ask = order.is_ask
                    order_type = "SL" if order.type == "stop-loss" else "TP"
                    return (order.market_index, order_type, price, qty, is_ask)
                except Exception as e:
                    logger.warning(f"订单解析失败: {e}")
                    return None

            sl1, tp1 = [], []
            sl2, tp2 = [], []

            for order_list in orders1.values():
                for o in order_list:
                    key = extract_order_key(o)
                    if key:
                        sym, typ, price, qty, is_ask = key
                        if typ == "SL":
                            sl1.append((sym, price, qty, is_ask))
                        else:
                            tp1.append((sym, price, qty, is_ask))
            
           

            for order_list in orders2.values():
                for o in order_list:
                    key = extract_order_key(o)
                    if key:
                        sym, typ, price, qty, is_ask = key
                        if typ == "SL":
                            sl2.append((sym, price, qty, is_ask))
                        else:
                            tp2.append((sym, price, qty, is_ask))


            logger.info(" ========================================")
            logger.info(f"sl1 orders:{sl1}" )
            logger.info(" ========================================")
            logger.info(f"tp1 orders:{tp1}" )
            logger.info(" ========================================")
            logger.info(f"sl2 orders:{sl2}" )
            logger.info(" ========================================")
            logger.info(f"tp2 orders:{tp2}" )

            # ========================================
            # 3. 配对校验：SL ↔ TP
            # ========================================
            def match_sl_tp(sl_list, tp_list, name_sl, name_tp):
                if len(sl_list) != len(tp_list):
                    logger.error(f"数量不匹配: {name_sl}({len(sl_list)}) ≠ {name_tp}({len(tp_list)})")
                    return False

                sl_set = set(sl_list)
                tp_opposite = {(sym, price, qty, not is_ask) for sym, price, qty, is_ask in tp_list}

                if sl_set != tp_opposite:
                    diff = sl_set - tp_opposite
                    if diff:
                        logger.error(f"{name_sl} 多出或不匹配: {diff}")
                    diff2 = tp_opposite - sl_set
                    if diff2:
                        logger.error(f"{name_tp} 多出或不匹配: {diff2}")
                    return False
                return True

            # service1.SL ↔ service2.TP
            if not match_sl_tp(sl1, tp2, "service1 SL", "service2 TP"):
                return False

            # service1.TP ↔ service2.SL
            if not match_sl_tp(tp1, sl2, "service1 TP", "service2 SL"):
                return False

            logger.info("SL/TP 订单完美对冲：方向相反、数量相等")
            logger.info(f"===  {service1.id} vs {service2.id} 对冲状态完美！===\n")
            return True

        except Exception as e:
            logger.error(f"校验崩溃: {e}\n{traceback.format_exc()}")
            raise e



def parse_arguments():
    parser = argparse.ArgumentParser(description='lighter hedge bot')
    parser.add_argument('-env_file', '--env_file', type=str)
  
    return parser.parse_args()

def load_py_config(file_path: str) -> dict:
    """
    动态 import 一个 .py 文件并返回 dict
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        print(f"[ERROR] Config file not found: {path}")
        sys.exit(1)

    print(f"[INFO] Loading Python config: {path}")

    spec = importlib.util.spec_from_file_location("config_module", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)   # 执行文件，变量会写入 mod.__dict__
    except Exception as e:
        print(f"[ERROR] Failed to execute config file: {e}")
        sys.exit(1)

    # 只取大写变量（约定），防止把 import 的包也带进来
    config = {k: v for k, v in mod.__dict__.items()}
    return config


# ========================================
# 启动
# ========================================
if __name__ == "__main__":
    # args = parse_arguments()
    # raw_cfg = load_py_config(args.env_file)
    # globals().update(raw_cfg)  
    # print(f"Loaded config: MULTIPLIER_QUANTITY={MULTIPLIER_QUANTITY}, HEDGE_INTERVAL_SECONDS={HEDGE_INTERVAL_SECONDS}, HEDGE_SYMBOLS={HEDGE_SYMBOLS}, WEBHOOK_URL={WEBHOOK_URL}, SL={SL}, TP={TP}, number of keys={len(keys)}")
    asyncio.run(Hedge_Bot().trading_loop())

