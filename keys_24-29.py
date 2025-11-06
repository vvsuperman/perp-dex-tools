BASE_URL = "https://mainnet.zklighter.elliot.ai"
# 杠杆倍数，总仓位min(balance1, balance2) * MULTIPLIER_QUANTITY 
MULTIPLIER_QUANTITY = 4.5
# 10倍杠杆，0.09可能就被清算了
SL=0.08  # 止损比例
TP=0.08  # 止盈比例


# 两次交易间隔时间
HEDGE_INTERVAL_SECONDS = 3600

# random symbols 
HEDGE_SYMBOLS = ["PAXG","ASTER","MNT","PENDLE"]
#HEDGE_SYMBOLS = ["PAXG"]

# 告警地址
WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=7b588bb6ca84b8b7e8ff97af90021a12ac2c56e96e75670201318ab313779459"


# random symbols 
KEYS =[


     {  "id":'lumao24',
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"5d72d25750a439ede278e12e9d27699f899b3e926787504d3f92f500a38a398f1045658e85826546",
        "API_KEY_PUBLIC_KEY":"78dfb829f4c90dc000d9207513036ebcee8a9e9b3319bab91f1ab2c46d33eea1c575a6e12f8f6b5c",
        "LIGHTER_ACCOUNT_INDEX":348321,
        "LIGHTER_API_KEY_INDEX":3
    },


     {  "id":'lumao25',
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"5fe8c014f3793fe4a4f4384e43ed3ce794e3fbfb57c4df92c7fb0d80cef7b88b4d46cb81b6f7e269",
        "API_KEY_PUBLIC_KEY":"0dbb7c6e1cd21744b4e5a5086ac6efcf34dcc0d36fe8b607b38682628472e7036e1fa1fa439083d4",
        "LIGHTER_ACCOUNT_INDEX":348311,
        "LIGHTER_API_KEY_INDEX":3
    },


    {  "id":"lumao26",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"38498ce360470602c854f4b626143b361d6a26a755e142d9052e6d297785acc7d8c279a0e93a3c5c",
        "API_KEY_PUBLIC_KEY":"34c1df2ddd545bf15c190565d627cebae79a60207f27c2de0155267e9ce68567ec3177c818d9f831",
        "LIGHTER_ACCOUNT_INDEX":348342,
        "LIGHTER_API_KEY_INDEX":3,
    },
    
    {  "id":"lumao27",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"73d4693e32de0f9170f1189068ba283ce0e247bf815ffd67185b95158b8c6e561176497401a3c67a",
        "API_KEY_PUBLIC_KEY":"1680a9fef621032ee1371e303e578c051aa46a830f0280caa45b893fb8380357aa357a07ac363ed8",
        "LIGHTER_ACCOUNT_INDEX":348332,
        "LIGHTER_API_KEY_INDEX":3
    },
    {  
        "id":"lumao28",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"b181851444b4a75b6af94715be792a94a781fb8d5d22834ae33aaf6f99695ae4c0fb6f66b156b667",
        "API_KEY_PUBLIC_KEY":"a100320814bbee87f0ec855e57e5a004134e647a81ef9bef91691258a52a7871174de6e3301b463b",
        "LIGHTER_ACCOUNT_INDEX":348353,
        "LIGHTER_API_KEY_INDEX":3
    
    },
    { 
        "id":"lumao29",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"b6abc4225c62559775cb22d3a9e959075ae5427347df7b82cff54268ad079f054a84808e9ec09736",
        "API_KEY_PUBLIC_KEY":"9a78c8e851cdc5977ad3a342ccde4c0faebbd705b75fc94bf773fd10dc49e2437097cf55786fa906",
        "LIGHTER_ACCOUNT_INDEX":348387,
        "LIGHTER_API_KEY_INDEX":3
    
    },

]