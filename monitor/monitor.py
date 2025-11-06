import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi import Request   # ← 新增这行

import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from decimal import Decimal
import logging
import json
from typing import List, Dict
from exchanges.lighter_service import Lighter_Service

# === 你的 lighter 导入 ===
from lighter import ApiClient, Configuration
import lighter
from lighter.signer_client import SignerClient

# === 本地模块 ===
from monitor.db import Lighter_Dao
lighter_dao = Lighter_Dao()
from keys import KEYS, BASE_URL

from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    asyncio.create_task(scheduler())
    yield
    # 关闭时（可选）
    # pass

app = FastAPI(lifespan=lifespan)

# app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monitor")

# === 客户端缓存 ===
lighter_service_dict: Dict[str, 'Lighter_Service'] = {}

def get_service(config) -> Lighter_Service:
    key = f"{config['LIGHTER_ACCOUNT_INDEX']}_{config['LIGHTER_API_KEY_INDEX']}"
    if key not in lighter_service_dict:
        lighter_service_dict[key] = Lighter_Service(config)
    return lighter_service_dict[key]


    

# ========================================
# 定时任务
# ========================================
async def fetch_balance_task(config):
    lighter_service = get_service(config)
    id = config['id']
    account_id = str(config['LIGHTER_ACCOUNT_INDEX'])
    try:
        # client.initial_client()
        account = await lighter_service.get_account_with_retry()
        balance = Decimal(account.total_asset_value)
        pnl = lighter_dao.save_snapshot(account_id, balance)
        logger.info(f"账户 {id} | Balance: {balance} | PNL: {pnl:+.2f}")
    except Exception as e:
        logger.error(f"账户 {id} 错误: {e}")

async def run_monitor():
    tasks = [fetch_balance_task(cfg) for cfg in KEYS]
    await asyncio.gather(*tasks)

async def scheduler():
    while True:
        logger.info("每小时监控开始...")
        await run_monitor()
        await asyncio.sleep(3600)

# ========================================
# API
# ========================================
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html") as f:
        return f.read()

@app.get("/api/accounts")
async def api_accounts(request: Request):
    # 读取查询参数（YYYY-MM-DD）
    query = request.query_params
    start_date = query.get("start")   # 示例: "2025-10-01"
    end_date   = query.get("end")     # 示例: "2025-10-31"
    
    all_data = []

    for key in KEYS:
        # account_id = row['account_id']
        # config = next(c for c in KEYS if str(c['LIGHTER_ACCOUNT_INDEX']) == account_id)
        lighter_service = get_service(key)

        try:
            account = await lighter_service.get_account_with_retry()
            initial_balance = lighter_dao.get_initial_balance(key['LIGHTER_ACCOUNT_INDEX'])

            balance = Decimal(account.total_asset_value)
            pnl = balance - initial_balance

            # volume = lighter_dao.get_position_amount_sum_by_account(key['LIGHTER_ACCOUNT_INDEX'])
            volume = lighter_dao.get_position_amount_sum_by_account(
                key['LIGHTER_ACCOUNT_INDEX'],
                start_time=f"{start_date}T00:00:00" if start_date else None,
                end_time=f"{end_date}T23:59:59"     if end_date   else None
            )

            positions_raw = account.positions
            positions = []
            for p in positions_raw:
               
                if Decimal(p.position) == 0: continue
                size = abs(Decimal(p.position))
                positions.append({
                    "symbol": p.symbol,
                    "side": "多" if p.sign == 1 else "空",
                    "size": float(size),
                    "position_value": float(Decimal(p.position_value)),
                    "entry_price": float(Decimal(p.avg_entry_price)) ,
                    "liq_price": float(Decimal(p.liquidation_price)),
                    "unrealized_pnl": float(Decimal(p.unrealized_pnl)) ,
                })

            orders = []
            symbols = {p.symbol for p in positions_raw if Decimal(p.position) != 0}
            for symbol in symbols:
                try:     
                    active = await lighter_service.fetch_active_orders_with_retry(symbol)
                    for o in active:
                       
                        orders.append({
                            "symbol": symbol,
                            "type": o.type,                           
                            "size": o.remaining_base_amount ,
                            "price": o.trigger_price
                        })
                except: pass

            all_data.append({
                "account_id": lighter_service.id,
                "initial_balance": float(initial_balance),   # 新增
                "balance": balance,
                "pnl": pnl,
                "volume": volume,
                "positions": positions,
                "orders": orders
            })
        except Exception as e:
            logger.error(f"实时数据失败 {lighter_service.id}: {e}")
            all_data.append({"account_id": lighter_service.id, "balance": balance, "pnl": pnl, "positions": [], "orders": []})

    html = '''
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>账户</th>
                    <th>开始金额</th>
                    <th>余额</th>
                    <th>PNL</th>
                    <th>交易量</th>
                    <th>挂单</th>
                </tr>
            </thead>
            <tbody>
        '''

    total_initial = Decimal(0.0)
    total_balance = Decimal(0.0)
    total_pnl = Decimal(0.0)
    total_volume_all = Decimal(0.0)

    for d in all_data:
       
        
        total_initial += Decimal(d['initial_balance'])
        total_balance += Decimal(d['balance'])
        total_pnl += Decimal(d['pnl'])
        total_volume_all += Decimal(d['volume'])

        pnl_class = "pnl-positive" if d['pnl'] >= 0 else "pnl-negative"

        # 持仓摘要
        pos_summary = "<br>".join([
            f'<span class="position-{"long" if p["side"]=="多" else "short"}">{p["symbol"]} {p["side"]} {p["size"]:.4f}</span>'
            for p in d['positions'][:3]
        ])
        if len(d['positions']) > 3:
            pos_summary += f'<br><small>共 {len(d["positions"])} 个</small>'
        pos_summary += f'<br><a class="text-primary small" data-bs-toggle="collapse" href="#pos-{d["account_id"]}" role="button">展开</a>'

        pos_detail = ""
        if d['positions']:
            pos_detail = f'<div class="collapse mt-2" id="pos-{d["account_id"]}"><div class="card card-body p-2">'
            pos_detail += '<table class="table table-sm table-bordered mb-0"><thead class="table-light"><tr>'
            pos_detail += '<th>Symbol</th><th>方向</th><th>Size</th><th>价值</th><th>入场价</th><th>清算价</th><th>未实现PNL</th>'
            pos_detail += '</tr></thead><tbody>'
            for p in d['positions']:
                side_class = 'text-success' if p['side']=='多' else 'text-danger'
                pnl_class_pos = 'text-success' if p['unrealized_pnl'] >= 0 else 'text-danger'
                pos_detail += f'''
                <tr>
                    <td>{p["symbol"]}</td>
                    <td class="{side_class}"><strong>{p["side"]}</strong></td>
                    <td>{p["size"]:.6f}</td>
                    <td>{p["position_value"]:,.2f}</td>
                    <td>{p["entry_price"]:,.4f}</td>
                    <td>{p["liq_price"]:,.4f}</td>
                    <td class="{pnl_class_pos}">{p["unrealized_pnl"]:+.2f}</td>
                </tr>
                '''
            pos_detail += '</tbody></table></div></div>'

        # 挂单摘要 + 原始数据
        order_summary = f'{len(d["orders"])} 个'
        if d['orders']:
            order_summary += f'<br><a class="text-primary small" data-bs-toggle="collapse" href="#ord-{d["account_id"]}" role="button">展开</a>'

        order_detail = ""
        if d['orders']:
            order_detail = f'<div class="collapse mt-2" id="ord-{d["account_id"]}"><div class="card card-body p-2">'
            order_detail += '<table class="table table-sm table-bordered mb-0"><thead class="table-light"><tr>'
            order_detail += '<th>Symbol</th><th>Type</th><th>Size (raw)</th><th>Price (raw)</th>'
            order_detail += '</tr></thead><tbody>'
            for o in d['orders']:
                order_detail += f'''
                <tr>
                    <td>{o["symbol"]}</td>
                    <td>{o["type"]}</td>
                    <td>{o["size"]}</td>
                    <td>{o["price"]}</td>
                </tr>
                '''
            order_detail += '</tbody></table></div></div>'

        # 每行
        html += f'''
        <tr>
            <td><strong>{d["account_id"]}</strong></td>
            <td>${d["initial_balance"]:,.2f}</td>
            <td>${float(d["balance"]):,.2f}</td>
            <td class="{pnl_class}"><strong>{d["pnl"]:+.2f}</strong></td>
            <td>${d["volume"]:,.2f}</td>  <
            <td><small>{pos_summary}</small>{pos_detail}</td>
            <td><small>{order_summary}</small>{order_detail}</td>
        </tr>
        '''

    # 合计行
    total_pnl_class = "pnl-positive" if total_pnl >= 0 else "pnl-negative"
    html += f'''
        <tr class="table-primary fw-bold">
            <td>合计</td>
            <td>${total_initial:,.2f}</td>
            <td>${total_balance:,.2f}</td>
            <td class="{total_pnl_class}">{total_pnl:+.2f}</td>
            <td>${total_volume_all:,.2f}</td>  <!-- 新增 -->
            <td colspan="2"></td>
        </tr>
    '''
    html += '</tbody></table>'
    return HTMLResponse(html if all_data else "暂无数据")
# @app.on_event("startup")
# async def startup():
#     asyncio.create_task(scheduler())

if __name__ == "__main__":
    uvicorn.run("monitor:app", host="0.0.0.0", port=8800, reload=False)