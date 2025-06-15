"""
設定ファイル
"""

# データファイルのパス
DATA_FILE_PATH = "./data/economic_data.csv"

# サーバー設定
HOST = '127.0.0.1'
PORT = 8888
DEBUG = False

# サーバー安定性設定
THREADED = True
USE_RELOADER = False

# グラフの色設定
GRAPH_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

# データタグの設定
DATA_TAG_CONFIGS = {
    'CPI': {
        'display_name': 'Consumer Price Index',
        'unit': '%',
        'description': '消費者物価指数'
    },
    'GDP': {
        'display_name': 'Gross Domestic Product',
        'unit': '%',
        'description': '国内総生産'
    },
    'Retail': {
        'display_name': 'Retail Sales',
        'unit': '%',
        'description': '小売売上高'
    },
    'Employment': {
        'display_name': 'Employment Change',
        'unit': 'K',
        'description': '雇用者数変化'
    },
    'Unemployment': {
        'display_name': 'Unemployment Rate',
        'unit': '%',
        'description': '失業率'
    }
}

# 通貨の設定
CURRENCY_CONFIGS = {
    'USD': {'display_name': 'US Dollar', 'country': 'United States'},
    'JPY': {'display_name': 'Japanese Yen', 'country': 'Japan'},
    'EUR': {'display_name': 'Euro', 'country': 'European Union'},
    'GBP': {'display_name': 'British Pound', 'country': 'United Kingdom'},
    'AUD': {'display_name': 'Australian Dollar', 'country': 'Australia'}
}