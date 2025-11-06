# lumao 18-23
BASE_URL = "https://mainnet.zklighter.elliot.ai"
# 杠杆倍数，总仓位min(balance1, balance2) * MULTIPLIER_QUANTITY 
MULTIPLIER_QUANTITY = 4.5
# 10倍杠杆，0.09可能就被清算了
SL=0.08  # 止损比例
TP=0.08  # 止盈比例


# 两次交易间隔时间
HEDGE_INTERVAL_SECONDS = 3600*5

# random symbols 
# HEDGE_SYMBOLS = ["PAXG","ASTER","MNT","PENDLE"]
HEDGE_SYMBOLS = ["PAXG"]


# 告警地址
WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=7b588bb6ca84b8b7e8ff97af90021a12ac2c56e96e75670201318ab313779459"

BASE_URL = "https://mainnet.zklighter.elliot.ai"
# 杠杆倍数，总仓位min(balance1, balance2) * MULTIPLIER_QUANTITY 
MULTIPLIER_QUANTITY = 4.5
# 10倍杠杆，0.09可能就被清算了
SL=0.12  # 止损比例
TP=0.12  # 止盈比例


# 两次交易间隔时间
HEDGE_INTERVAL_SECONDS = 3600*5

# random symbols 
KEYS =[


     {  "id":'lumao18',
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"790921abc67281cfe4ad54c03865e25e2c36f5f8b02d9445a24304579fc90eb304aea7574696cd3e",
        "API_KEY_PUBLIC_KEY":"b8e13fc10bd13a41322012a2957325aa08deb679fadfe165af0265cd8a543f137f85b30a4c2f37c5",
        "LIGHTER_ACCOUNT_INDEX":346402,
        "LIGHTER_API_KEY_INDEX":3
    },


     {  "id":'lumao19',
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"bcb79a090eb40adcab361ffca97db0e915f9ce401a821c77f4678cdddf86697f77f38d920a657d6e",
        "API_KEY_PUBLIC_KEY":"e7c9186cfa16fa0e47823fdde84affba1e63e773d5f976fcbf1ea12e209f5602597b17ce8c7e2ab1",
        "LIGHTER_ACCOUNT_INDEX":346438,
        "LIGHTER_API_KEY_INDEX":3
    },


    {  "id":"lumao20",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"f903cebbb8fc9e90bd788245a725689c4f88dae8d9c17f5f9db7f06ede055f672a4d1d463df40548",
        "API_KEY_PUBLIC_KEY":"1a0370ca98bbfc4251fdfaeaa714e02586fed530cafeee302d78c0b1454fec8d933251b4fad0dd57",
        "LIGHTER_ACCOUNT_INDEX":346828,
        "LIGHTER_API_KEY_INDEX":3,
    },
    
    {  "id":"lumao21",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"30231da7e3e162acb1fd9a0b27fa6cff958ee652309118039c427819de082f82e0206ded82cbd651",
        "API_KEY_PUBLIC_KEY":"79126cea52eb9ba2295eccda64043c9ae4f94decb25919a9afc8373a90d4ed6b256a15cf0a338979",
        "LIGHTER_ACCOUNT_INDEX":346505,
        "LIGHTER_API_KEY_INDEX":3
    },
    {  
        "id":"lumao22",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"7bd1568bca639336e67f99221e40eefac761f4d26e89339c9ea3fc76953305987f20efe61139d30d",
        "API_KEY_PUBLIC_KEY":"d5e65621e1d2c91891aae1c792faa8caf9a8f4fae08fc3486d6d2ed82413d22fce42fb69ae234949",
        "LIGHTER_ACCOUNT_INDEX":346540,
        "LIGHTER_API_KEY_INDEX":3
    
    },
    { 
        "id":"lumao23",
        "exchange": "lighter",
        "API_KEY_PRIVATE_KEY":"ba97bd6fa4091e72b3a3706016796b34640bf847d19a71200f7c507dadf8b2a95a29419acde0257b",
        "API_KEY_PUBLIC_KEY":"cb9d557ea0129c29ede3adebfc3efdeb51e725c88c75dd5fa40da047fb7f708245fc649c16c9f10a",
        "LIGHTER_ACCOUNT_INDEX":346727,
        "LIGHTER_API_KEY_INDEX":3
    
    },

]