BASE_URL = "https://mainnet.zklighter.elliot.ai"
# 杠杆倍数，总仓位min(balance1, balance2) * MULTIPLIER_QUANTITY 
MULTIPLIER_QUANTITY = 5
# 10倍杠杆，0.09可能就被清算了
SL=0.08  # 止损比例
TP=0.08  # 止盈比例


# 两次交易间隔时间
HEDGE_INTERVAL_SECONDS = 3600

# random symbols 
#HEDGE_SYMBOLS = ["PAXG","ASTER","MNT","PENDLE"]
HEDGE_SYMBOLS = ["BTC","ETH"]
#HEDGE_SYMBOLS = ["PAXG"]

# 告警地址
WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=7b588bb6ca84b8b7e8ff97af90021a12ac2c56e96e75670201318ab313779459"


# random symbols 
KEYS =[


     {  "id":'lumao30',
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"03690f3c693e785669ed0b015bb000e1ed0da5cd207e81ad4079ff0547a1e7fcaf00fb07de81315f",
        "API_KEY_PUBLIC_KEY":"879c42f444098c7486e8e7671d8bd6c813aa211639f48709918fd7ba5b2b39cc16d56774ce651b14",
        "LIGHTER_ACCOUNT_INDEX":349654,
        "LIGHTER_API_KEY_INDEX":3
    },


     {  "id":'lumao31',
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"a0558ff499394313cc32570ebe3f7d57010e33da641777fab842c56d42dc0b3fe93880d2047a431a",
        "API_KEY_PUBLIC_KEY":"ad776b108b18327faf9349defe4544643a179ff406bc53f49bb2b4349a38017c5b47497d3595bf80",
        "LIGHTER_ACCOUNT_INDEX":349706,
        "LIGHTER_API_KEY_INDEX":3
    },


    {  "id":"lumao32",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"4e594d91b7ea775c44f4dec0803af91020481e103a424546c4d3eb507e6634d426cc226ccee3fa33",
        "API_KEY_PUBLIC_KEY":"f5b0a557f579373ad9e02530cce6cd1d8178d17072a11fc5b0f3a454d3877f785ac38a4cf523a4ad",
        "LIGHTER_ACCOUNT_INDEX":349685,
        "LIGHTER_API_KEY_INDEX":3,
    },
    
    {  "id":"lumao33",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"956ce73da96039f59723712e01cbe8c111c17887f2bd60923ed960eca46a441e9f53898851b6536d",
        "API_KEY_PUBLIC_KEY":"afce30f7f7be5a5fd7fa13447b75f5ee3c7548afb64ae776c680b747c7c8f1d348efee97973739ad",
        "LIGHTER_ACCOUNT_INDEX":349740,
        "LIGHTER_API_KEY_INDEX":3
    },
    {  
        "id":"lumao34",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"31872bffa45e68723408c50a777cdeb0daaf37c2082705358cbe6644b0b8e00e911b5a0e4d164c2c",
        "API_KEY_PUBLIC_KEY":"ad4a5aaf1fe9f907aafb75a5909f6fdc426e0a6ccf7f28c035c0b4f4232a95654c5b17b4357cd211",
        "LIGHTER_ACCOUNT_INDEX":349731,
        "LIGHTER_API_KEY_INDEX":3
    
    },
    { 
        "id":"lumao35",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"a76b5d117471e6ed25490dc72ca0834a0c4c59e94fc2c294d653f786a7837dda91774d8341692329",
        "API_KEY_PUBLIC_KEY":"3435fcf72816b8892a181f18ae861577dfb571dadbe638639f06478d6de0bf5def91f19ce7cb8ce6",
        "LIGHTER_ACCOUNT_INDEX":355827,
        "LIGHTER_API_KEY_INDEX":3
    
    },

]