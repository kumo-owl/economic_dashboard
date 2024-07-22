import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from dash.dash_table import DataTable

# データの読み込みと前処理
df = pd.read_csv("./data/economic_data.csv")
df["date"] = pd.to_datetime(df["date"], dayfirst=True)
df["data_tag"] = "None"

# CPIデータのフィルタリングとデータタグの更新
cpi_conditions = [
    (df['currency'] == 'USD') & (df['event'].str.contains(r'^CPI \(YoY\)')),
    (df['currency'] == 'JPY') & (df['event'].str.contains(r'BoJ Core CPI \(YoY\)')),
    (df['currency'] == 'EUR') & (df['event'].str.contains(r'^CPI \(YoY\)')),
    (df['currency'] == 'GBP') & (df['event'].str.contains(r'^CPI \(YoY\)')),
    (df['currency'] == 'AUD') & (df['event'].str.contains(r'^CPI \(YoY\)'))
]

for condition in cpi_conditions:
    df.loc[condition, 'data_tag'] = 'CPI'
    df.loc[condition, ['actual', 'forecast', 'previous']] = df.loc[condition, ['actual', 'forecast', 'previous']].apply(lambda x: x.str.replace('%', '', regex=True).astype(float))

# GDPデータのフィルタリングとデータタグの更新
gdp_conditions = [
    (df['currency'] == 'USD') & (df['event'].str.contains(r'^GDP \(QoQ\)')),
    (df['currency'] == 'JPY') & (df['event'].str.contains(r'^GDP \(YoY\)')),
    (df['currency'] == 'EUR') & (df['event'].str.contains(r'^GDP \(YoY\)')),
    (df['currency'] == 'GBP') & (df['event'].str.contains(r'^GDP \(YoY\)')),
    (df['currency'] == 'AUD') & (df['event'].str.contains(r'^GDP \(YoY\)'))
]

for condition in gdp_conditions:
    df.loc[condition, 'data_tag'] = 'GDP'
    df.loc[condition, ['actual', 'forecast', 'previous']] = df.loc[condition, ['actual', 'forecast', 'previous']].apply(lambda x: x.str.replace('%', '', regex=True).astype(float))

# 小売売上高データのフィルタリングとデータタグの更新
retail_conditions = [
    (df['currency'] == 'USD') & (df['event'].str.contains(r'^Retail Sales \(YoY\)')),
    (df['currency'] == 'JPY') & (df['event'].str.contains(r'^Retail Sales \(YoY\)')),
    (df['currency'] == 'EUR') & (df['event'].str.contains(r'^Retail Sales \(YoY\)')),
    (df['currency'] == 'GBP') & (df['event'].str.contains(r'^Retail Sales \(YoY\)')),
    (df['currency'] == 'AUD') & (df['event'].str.contains(r'^Retail Sales \(QoQ\)'))
]

for condition in retail_conditions:
    df.loc[condition, 'data_tag'] = 'Retail'
    df.loc[condition, ['actual', 'forecast', 'previous']] = df.loc[condition, ['actual', 'forecast', 'previous']].apply(lambda x: x.str.replace('%', '', regex=True).astype(float))

# 雇用者数
payroll_conditions = [
    (df['currency'] == 'USD') & (df['event'].str.contains(r'^Nonfarm Payroll')),
    (df['currency'] == 'GBP') & (df['event'].str.contains(r'^Employment Change')),
    (df['currency'] == 'AUD') & (df['event'].str.contains(r'^Employment Change'))
]

for condition in payroll_conditions:
    df.loc[condition, 'data_tag'] = 'Employment'
    df.loc[condition, ['actual', 'forecast', 'previous']] = df.loc[condition, ['actual', 'forecast', 'previous']].apply(lambda x: x.str.replace('K', '', regex=True).replace(',', '', regex=True).astype(float))

#失業率
unemployment_rate_conditions = [
    (df['currency'] == 'USD') & (df['event'].str.contains(r'^Unemployment')),
    (df['currency'] == 'JPY') & (df['event'].str.contains(r'^Unemployment')),
    (df['currency'] == 'EUR') & (df['event'].str.contains(r'^Unemployment')),
    (df['currency'] == 'GBP') & (df['event'].str.contains(r'^Unemployment')),
    (df['currency'] == 'AUD') & (df['event'].str.contains(r'^Unemployment'))
]

for condition in unemployment_rate_conditions:
    df.loc[condition, 'data_tag'] = 'Unemployment'
    df.loc[condition, ['actual', 'forecast', 'previous']] = df.loc[condition, ['actual', 'forecast', 'previous']].apply(lambda x: x.str.replace('%', '', regex=True).astype(float))

# 通貨別のデータフィルタリング
currency_data = df.groupby('currency')

# Dashアプリケーションの設定
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# グラフ作成関数
def create_graph(data, title, yaxis_title, value_type):
    fig = go.Figure()
    for tag in data['data_tag'].unique():
        if tag != "None" and tag != "Employment":
            filtered_data = data[data['data_tag'] == tag]
            fig.add_trace(go.Scatter(x=filtered_data['date'], y=filtered_data[value_type], mode='lines', name=f'{tag} {value_type.capitalize()}', showlegend=True ))
    fig.update_layout(title=title, xaxis_title='Date', yaxis_title=yaxis_title)
    return fig

def create_employment_graph(data, title, yaxis_title, value_type):
    fig = go.Figure()
    for tag in data['data_tag'].unique():
        if tag == "Employment":
            filtered_data = data[data['data_tag'] == tag]
            fig.add_trace(go.Scatter(
                x=filtered_data['date'],
                y=filtered_data[value_type],
                mode='lines',
                name=f'{tag} {value_type.capitalize()}',
                showlegend=True  # 凡例を表示
            ))
    fig.update_layout(title=title, xaxis_title='Date', yaxis_title=yaxis_title)
    return fig


# 指標別グラフ作成関数（各通貨比較）
def create_indicator_graph(data, title, yaxis_title, value_type):
    fig = go.Figure()
    for tag in data['data_tag'].unique():
        if tag != "None":
            filtered_tag_data = data[data['data_tag'] == tag]
            for currency in filtered_tag_data['currency'].unique():
                filtered_data = filtered_tag_data[filtered_tag_data['currency'] == currency]
                fig.add_trace(go.Scatter(x=filtered_data['date'], y=filtered_data[value_type], mode='lines', name=f'{currency} {tag} {value_type.capitalize()}'))
    fig.update_layout(title=title, xaxis_title='Date', yaxis_title=yaxis_title)
    return fig

# Dashアプリケーションのレイアウト設定
app.layout = html.Div([
    html.H1("Economic Data Dashboard"),
    dcc.Tabs(id="tabs", children=[
        dcc.Tab(label='Currency', children=[
            html.Div([
                dcc.Dropdown(
                    id='currency-dropdown',
                    options=[{'label': currency, 'value': currency} for currency in currency_data.groups.keys()],
                    value=list(currency_data.groups.keys())[0]
                ),
                dcc.Dropdown(
                    id='value-type-dropdown-currency',
                    options=[
                        {'label': 'Forecast', 'value': 'forecast'},
                        {'label': 'Actual', 'value': 'actual'}
                    ],
                    value='forecast'
                ),
                dcc.Graph(id='currency-graph', style={'width': '100%', 'height': '80vh'}),
            ])
        ]),
        dcc.Tab(label='Indicator', children=[
            html.Div([
                dcc.Dropdown(
                    id='indicator-dropdown',
                    options=[{'label': indicator, 'value': indicator} for indicator in df['data_tag'].unique() if indicator != "None"],
                    value=[indicator for indicator in df['data_tag'].unique() if indicator != "None"][0]
                ),
                dcc.Dropdown(
                    id='value-type-dropdown-indicator',
                    options=[
                        {'label': 'Forecast', 'value': 'forecast'},
                        {'label': 'Actual', 'value': 'actual'}
                    ],
                    value='forecast'
                ),
                dcc.Graph(id='indicator-graph', style={'width': '100%', 'height': '80vh'}),
            ])
        ])
    ])
])




from plotly.subplots import make_subplots

def create_combined_graph(data, currency_title, employment_title, yaxis_title, value_type):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=[currency_title, employment_title])

    # 通貨別グラフ
    for tag in data['data_tag'].unique():
        if tag != "None" and tag != "Employment":
            filtered_data = data[data['data_tag'] == tag]
            fig.add_trace(go.Scatter(x=filtered_data['date'], y=filtered_data[value_type], mode='lines', name=f'{tag} {value_type.capitalize()}'), row=1, col=1)

    # 雇用者数グラフ
    for tag in data['data_tag'].unique():
        if tag == "Employment":
            filtered_data = data[data['data_tag'] == tag]
            fig.add_trace(go.Scatter(x=filtered_data['date'], y=filtered_data[value_type], mode='lines', name=f'{tag} {value_type.capitalize()}'), row=2, col=1)

    fig.update_layout(height=800, title_text="Economic Indicators")
    fig.update_xaxes(title_text='Date', row=1, col=1, showticklabels=True)
    fig.update_xaxes(title_text='Date', row=2, col=1, showticklabels=True)
    fig.update_yaxes(title_text=yaxis_title, row=1, col=1)
    fig.update_yaxes(title_text=yaxis_title, row=2, col=1)
    return fig




@app.callback(
    Output('currency-graph', 'figure'),
    [Input('currency-dropdown', 'value'), Input('value-type-dropdown-currency', 'value')]
)
def update_currency_graph(selected_currency, selected_value_type):
    data = df[(df['currency'] == selected_currency) & (df['data_tag'] != "None")]
    currency_title = f"{selected_currency} Economic Indicators ({selected_value_type.capitalize()})"
    employment_title = f"{selected_currency} Employment Data ({selected_value_type.capitalize()})"
    return create_combined_graph(data, currency_title, employment_title, 'Value', selected_value_type)



# コールバック関数：指標別グラフと表の更新
@app.callback(
    Output('indicator-graph', 'figure'),
    [Input('indicator-dropdown', 'value'), Input('value-type-dropdown-indicator', 'value')]
)
def update_indicator_graph(selected_indicator, selected_value_type):
    data = df[(df['data_tag'] == selected_indicator) & (df['data_tag'] != "None")]
    title = f"{selected_indicator} Across Currencies ({selected_value_type.capitalize()})"
    return create_indicator_graph(data, title, 'Value', selected_value_type)

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=5050, debug=True)
