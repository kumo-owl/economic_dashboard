#!/usr/bin/env python3
"""
フル機能 Streamlit 経済ダッシュボード（接続安定化版）
"""

import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import os
import requests
import json
import investpy

# ページ設定
st.set_page_config(
    page_title="📊 Economic Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ダークテーマ用CSS
st.markdown("""
<style>
    .stApp {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    .stSelectbox > div > div {
        background-color: #3d3d3d;
        color: #ffffff;
    }
    .stMetric {
        background-color: #2d2d2d;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .main-header {
        text-align: center;
        color: #4CAF50;
        font-size: 3rem;
        margin-bottom: 2rem;
    }
    .status-indicator {
        position: fixed;
        top: 10px;
        right: 10px;
        background-color: #4CAF50;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 12px;
        z-index: 1000;
    }
</style>
""", unsafe_allow_html=True)

# 接続状態表示
st.markdown(f'<div class="status-indicator">🟢 Live • {time.strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)


def fetch_fallback_data():
    """フォールバック用の簡単なデータ取得"""
    try:
        # 最小限のAPIからデータ取得を試行
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                st.info(f"🔄 フォールバックAPIから {len(df)}件のデータを取得")
                return df
    except Exception as e:
        st.warning(f"フォールバックも失敗: {e}")
    
    return None

def update_data_file():
    """月ごとのデータファイルを更新"""
    try:
        # ディレクトリ作成
        os.makedirs("./data", exist_ok=True)
        
        # 過去5年分のデータを取得
        today = datetime.now()
        months_to_fetch = []
        
        # 過去5年分 + 将来1ヶ月分のデータを取得（61ヶ月）
        for i in range(-1, 60):  # -1で1ヶ月先も含む
            target_date = today - timedelta(days=30*i)
            months_to_fetch.append(target_date)
        
        total_new_data = 0
        
        for target_date in months_to_fetch:
            year_month = target_date.strftime('%Y-%m')
            monthly_file = f"./data/economic_data_{year_month}.csv"
            
            # 月ごとのファイルが存在しないか、古い場合は更新
            update_needed = False
            
            if os.path.exists(monthly_file):
                file_time = datetime.fromtimestamp(os.path.getmtime(monthly_file))
                # 6時間以上古い場合は更新
                if datetime.now() - file_time > timedelta(hours=6):
                    update_needed = True
                    # データ更新メッセージを削除
            else:
                update_needed = True
                # 新規データ取得メッセージを削除
            
            if update_needed:
                with st.spinner(f"🔄 {year_month} の経済データを取得中..."):
                    # 月の開始日と終了日を計算
                    first_day = target_date.replace(day=1)
                    if target_date.month == 12:
                        last_day = target_date.replace(year=target_date.year+1, month=1, day=1) - timedelta(days=1)
                    else:
                        last_day = target_date.replace(month=target_date.month+1, day=1) - timedelta(days=1)
                    
                    from_date = first_day.strftime('%d/%m/%Y')
                    # 将来の日付も含めて取得（investpyで将来カレンダー取得可能）
                    to_date = last_day.strftime('%d/%m/%Y')
                    
                    # 月ごとのデータを取得
                    monthly_data = fetch_monthly_economic_data(from_date, to_date, year_month)
                    
                    if monthly_data is not None and not monthly_data.empty:
                        # 月ごとのファイルに保存
                        monthly_data.to_csv(monthly_file, index=False)
                        total_new_data += len(monthly_data)
                        # 成功メッセージは削除（最後にまとめて表示）
                    else:
                        st.warning(f"⚠️ {year_month}: データ取得に失敗")
        
        # 統合ファイルを作成
        create_combined_data_file()
        
        if total_new_data > 0:
            st.success(f"🎉 合計 {total_new_data}件の新しいデータを取得しました")
            # キャッシュをクリア
            load_data.clear()
        else:
            # 「最新です」メッセージは非表示に
            pass
            
    except Exception as e:
        st.error(f"データ更新エラー: {e}")
        # エラー時の情報は削除

def fetch_monthly_economic_data(from_date, to_date, year_month):
    """指定期間の経済データを取得（investpyを使用）"""
    try:
        # 取得期間の表示を削除
        
        # investpyで経済カレンダーデータを取得
        economic_data = investpy.economic_calendar(
            time_zone=None,
            countries=['united states', 'euro zone', 'united kingdom', 'japan', 'australia'],
            from_date=from_date,
            to_date=to_date
        )
        
        if not economic_data.empty:
            # デバッグ: 元の列名を確認
            # デバッグ情報は非表示
            
            # 通貨コードマッピング（zone列から）
            currency_mapping = {
                'united states': 'USD',
                'euro zone': 'EUR', 
                'united kingdom': 'GBP',
                'japan': 'JPY',
                'australia': 'AUD'
            }
            
            # zone列をcurrencyに変換
            if 'zone' in economic_data.columns:
                economic_data['currency'] = economic_data['zone'].map(currency_mapping).fillna(economic_data['zone'])
            else:
                economic_data['currency'] = 'Unknown'
            
            # 必要な列のみ選択して新しいDataFrameを作成
            result_data = {
                'date': economic_data.get('date', ''),
                'time': economic_data.get('time', ''),
                'currency': economic_data.get('currency', 'Unknown'),
                'importance': economic_data.get('importance', ''),
                'event': economic_data.get('event', ''),
                'actual': economic_data.get('actual', ''),
                'forecast': economic_data.get('forecast', ''),
                'previous': economic_data.get('previous', '')
            }
            
            result_df = pd.DataFrame(result_data)
            
            # IDカラムを追加
            result_df.insert(0, 'id', range(len(result_df)))
            
            return result_df
        else:
            return None
            
    except Exception as e:
        st.error(f"investpy {year_month} データ取得エラー: {e}")
        return fetch_fallback_data()

def create_combined_data_file():
    """月ごとのファイルを統合して単一のCSVファイルを作成"""
    try:
        data_files = []
        data_dir = "./data"
        
        # 月ごとのファイルを検索
        for filename in os.listdir(data_dir):
            if filename.startswith("economic_data_") and filename.endswith(".csv"):
                data_files.append(os.path.join(data_dir, filename))
        
        if data_files:
            combined_data = []
            total_files = len(data_files)
            
            # ファイルを静かに読み込み
            for file_path in sorted(data_files):
                try:
                    monthly_data = pd.read_csv(file_path)
                    combined_data.append(monthly_data)
                except Exception as e:
                    st.warning(f"⚠️ ファイル読み込みエラー: {file_path} - {e}")
            
            if combined_data:
                # 全データを結合
                all_data = pd.concat(combined_data, ignore_index=True)
                
                # 重複を除去
                all_data = all_data.drop_duplicates()
                
                # 統合ファイルに保存
                combined_file = "./data/economic_data.csv"
                all_data.to_csv(combined_file, index=False)
                
                st.success(f"📊 データ統合完了: {total_files}ファイルから{len(all_data)}件のデータを統合")
                
            else:
                st.warning("📁 統合可能なデータファイルが見つかりません")
        else:
            # ファイル未発見メッセージは削除
            pass
    except Exception as e:
        st.error(f"ファイル統合エラー: {e}")

@st.cache_data(ttl=1800, show_spinner=False)  # 30分キャッシュ
def load_data():
    """データの読み込みとキャッシュ（全データ）"""
    try:
        if not os.path.exists("./data/economic_data.csv"):
            st.error("データファイルが見つかりません")
            return pd.DataFrame()
            
        df = pd.read_csv("./data/economic_data.csv")
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['date'])
        df["data_tag"] = "None"
        
        # イベント名をクリーンアップ（月情報などを除去して正規化）
        def clean_event_name(event_name):
            import re
            if pd.isna(event_name):
                return ""
            # 月情報を除去して正規化
            cleaned = re.sub(r'\s*\([A-Z][a-z]{2}\)\s*$', '', str(event_name))  # (Feb), (Jan)などを除去
            return cleaned.strip()
        
        df['cleaned_event'] = df['event'].apply(clean_event_name)
        
        # 詳細な経済指標分類（地域・時期・種類を区別）
        tag_patterns = {
            # CPI関連（より詳細に分類）
            'National CPI (YoY)': r'National.*CPI.*\(YoY\)',
            'National CPI (MoM)': r'National.*CPI.*\(MoM\)',
            'Tokyo CPI (YoY)': r'Tokyo.*CPI.*\(YoY\)',
            'Tokyo CPI (MoM)': r'Tokyo.*CPI.*\(MoM\)',
            'Tokyo CPI Ex Food & Energy (YoY)': r'Tokyo.*CPI.*Ex.*Food.*Energy.*\(YoY\)|CPI.*Tokyo.*Ex.*Food.*Energy.*\(YoY\)',
            'Tokyo CPI Ex Food & Energy (MoM)': r'Tokyo.*CPI.*Ex.*Food.*Energy.*\(MoM\)|CPI.*Tokyo.*Ex.*Food.*Energy.*\(MoM\)',
            'Core CPI (YoY)': r'Core.*CPI.*\(YoY\)',
            'Core CPI (MoM)': r'Core.*CPI.*\(MoM\)',
            'CPI (YoY)': r'CPI.*\(YoY\)|Consumer.*Price.*Index.*\(YoY\)',
            'CPI (MoM)': r'CPI.*\(MoM\)|Consumer.*Price.*Index.*\(MoM\)',
            
            # 住宅関連
            'Housing Prices (YoY)': r'Housing.*Price.*\(YoY\)|HPI.*\(YoY\)|House.*Price.*\(YoY\)',
            'Housing Prices (MoM)': r'Housing.*Price.*\(MoM\)|HPI.*\(MoM\)|House.*Price.*\(MoM\)',
            'Building Permits': r'Building Permits|Construction.*Permits',
            'Housing Starts': r'Housing Starts|Home.*Starts',
            
            # 小売・消費関連
            'Retail Sales (YoY)': r'Retail Sales.*\(YoY\)',
            'Retail Sales (MoM)': r'Retail Sales.*\(MoM\)',
            'Consumer Confidence': r'Consumer Confidence|Consumer Sentiment',
            
            # 雇用関連
            'Employment Change': r'Employment Change|Nonfarm.*Payroll',
            'Unemployment Rate': r'Unemployment Rate',
            'Job Cuts (YoY)': r'Job.*Cuts.*\(YoY\)|Challenger.*Job.*Cuts.*\(YoY\)',
            'Jobless Claims': r'Initial.*Claims|Continuing.*Claims|Jobless.*Claims',
            
            # 製造業・PMI
            'Manufacturing PMI': r'Manufacturing.*PMI',
            'Services PMI': r'Services.*PMI|Service.*Sector.*PMI',
            'Composite PMI': r'Composite.*PMI',
            
            # 金融・金利
            'Interest Rate': r'Interest Rate|Fed.*Rate|BoJ.*Rate|ECB.*Rate|BoE.*Rate|RBA.*Rate|FOMC|Bank Rate|Cash Rate',
            'Money Supply (YoY)': r'Money Supply.*\(YoY\)|M[123].*Money.*Supply.*\(YoY\)',
            'Money Supply (MoM)': r'Money Supply.*\(MoM\)|M[123].*Money.*Supply.*\(MoM\)',
            
            # 貿易・商品
            'Trade Balance': r'Trade Balance|Current Account',
            'Commodity Prices (YoY)': r'Commodity.*Prices.*\(YoY\)',
            'Commodity Prices (MoM)': r'Commodity.*Prices.*\(MoM\)',
            
            # 産業生産
            'Industrial Production (YoY)': r'Industrial Production.*\(YoY\)',
            'Industrial Production (MoM)': r'Industrial Production.*\(MoM\)',
            
            # PPI関連
            'PPI (YoY)': r'PPI.*\(YoY\)|Producer.*Price.*\(YoY\)',
            'PPI (MoM)': r'PPI.*\(MoM\)|Producer.*Price.*\(MoM\)',
            
            # GDP関連
            'GDP (YoY)': r'GDP.*\(YoY\)',
            'GDP (QoQ)': r'GDP.*\(QoQ\)|GDP.*\(MoM\)',
            
            # その他
            'Factory Orders': r'Factory.*Orders|Manufacturing.*Orders',
            'Business Investment': r'Capital.*Expenditure|Business.*Investment|Capex',
            'Loans (YoY)': r'Loans.*\(YoY\)|Credit.*\(YoY\)'
        }
        
        # 指標を優先度順にマッチング（特定のものから先に）
        for tag, pattern in tag_patterns.items():
            # まだタグ付けされていない行のみマッチング
            untagged_mask = df['data_tag'] == 'None'
            pattern_mask = df['event'].str.contains(pattern, na=False, case=False)
            final_mask = untagged_mask & pattern_mask
            df.loc[final_mask, 'data_tag'] = tag
        
        # まだタグ付けされていないものは、クリーンアップしたイベント名をそのまま使用
        untagged_mask = df['data_tag'] == 'None'
        df.loc[untagged_mask, 'data_tag'] = df.loc[untagged_mask, 'cleaned_event']
            
        # 数値変換処理（全データに対して実行）
        for col in ['actual', 'forecast', 'previous']:
            if col in df.columns:
                # 数値変換処理
                def clean_numeric_value(value):
                    if pd.isna(value) or value == '':
                        return None
                    # 文字列に変換
                    str_val = str(value)
                    # カンマ、%、K、M、Bを除去
                    for char in [',', '%', 'K', 'M', 'B']:
                        str_val = str_val.replace(char, '')
                    # 数値に変換
                    try:
                        return float(str_val)
                    except:
                        return None
                
                df[col] = df[col].apply(clean_numeric_value)
        
        return df
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return pd.DataFrame()

def clean_and_interpolate_data(series):
    """データの前処理と線形補間"""
    try:
        # 数値に変換（元のインデックスを保持）
        numeric_series = pd.to_numeric(series, errors='coerce')
        
        # 0値をNaNに変換（ただし、実際に0が意味のある場合を考慮）
        mask_zero = numeric_series == 0
        if mask_zero.sum() > 0:
            # 前後の値と比較して異常な0値を検出
            zero_indices = numeric_series[mask_zero].index.tolist()
            
            for idx in zero_indices:
                try:
                    # 現在のインデックス位置を取得
                    current_pos = numeric_series.index.get_loc(idx)
                    
                    # 前の値を取得
                    prev_val = None
                    if current_pos > 0:
                        prev_data = numeric_series.iloc[:current_pos].dropna()
                        if len(prev_data) > 0:
                            prev_val = prev_data.iloc[-1]
                    
                    # 次の値を取得
                    next_val = None
                    if current_pos < len(numeric_series) - 1:
                        next_data = numeric_series.iloc[current_pos+1:].dropna()
                        if len(next_data) > 0:
                            next_val = next_data.iloc[0]
                    
                    # 前後の値が0でない場合、0値をNaNに変換
                    if prev_val is not None and next_val is not None:
                        if prev_val != 0 and next_val != 0:
                            numeric_series.loc[idx] = pd.NA
                            
                except (IndexError, KeyError, ValueError):
                    # インデックスエラーの場合はスキップ
                    continue
        
        # 前の値で穴埋め（forward fill）その後、線形補間
        filled_series = numeric_series.ffill()
        # 残ったNaN値は線形補間
        interpolated_series = filled_series.interpolate(method='linear')
        
        return interpolated_series
        
    except Exception as e:
        # エラーが発生した場合は元のシリーズを数値変換のみして返す
        st.warning(f"データ補間でエラーが発生しました: {e}")
        return pd.to_numeric(series, errors='coerce')

def get_indicator_unit_group(tag, sample_values):
    """指標の単位とスケールグループを判定（スケール細分化版）"""
    # サンプル値の範囲を確認
    numeric_values = pd.to_numeric(sample_values, errors='coerce').dropna()
    if len(numeric_values) == 0:
        return "other", "その他"
    
    value_range = numeric_values.max() - numeric_values.min()
    avg_value = abs(numeric_values.mean())
    max_value = numeric_values.max()
    min_value = numeric_values.min()
    
    # より厳密な指標名パターンマッチング
    tag_lower = tag.lower()
    
    # 1. PMI（50が基準）を優先
    if 'pmi' in tag_lower:
        return "index_50", "PMI (50基準)"
    
    # 2. 大規模な経済指標
    if any(x in tag_lower for x in ['gdp', 'trade balance', 'current account']):
        if avg_value > 1000000:  # 100万以上
            return "billions", "十億単位"
        elif avg_value > 1000:
            return "millions", "百万単位"
        else:
            # GDP成長率などの場合
            if max_value < 5:
                return "percentage_small", "率 (0-5%)"
            elif max_value < 10:
                return "percentage_medium", "率 (0-10%)"
            else:
                return "percentage_large", "率 (10%+)"
    
    # 3. 雇用・労働統計
    if any(x in tag_lower for x in ['claims', 'payroll', 'employment change', 'nonfarm']):
        if avg_value > 100000:  # 10万以上
            return "count_hundreds_k", "件数 (10万)"
        elif avg_value > 1000:
            return "count_thousands", "件数 (千)"
        else:
            return "count_units", "件数"
    
    # 4. 率・パーセンテージ指標の細分化
    percentage_patterns = [
        'rate', 'unemployment', 'interest', '(yoy)', '(mom)', '(qoq)',
        'inflation', 'change', 'growth'
    ]
    if any(pattern in tag_lower for pattern in percentage_patterns):
        if avg_value < 50:  # 一般的な率は50%以下
            # スケールでさらに細分化
            if 'interest' in tag_lower or 'fed rate' in tag_lower or 'bank rate' in tag_lower:
                return "percentage_interest", "金利 (0-5%)"
            elif 'unemployment' in tag_lower:
                return "percentage_unemployment", "失業率 (0-20%)"
            elif 'inflation' in tag_lower or 'cpi' in tag_lower:
                if min_value < -2:
                    return "percentage_inflation_neg", "インフレ率 (-5~+15%)"
                else:
                    return "percentage_inflation", "インフレ率 (0-10%)"
            elif max_value < 5:
                return "percentage_small", "率 (0-5%)"
            elif max_value < 10:
                return "percentage_medium", "率 (0-10%)"
            elif max_value < 20:
                return "percentage_large", "率 (0-20%)"
            else:
                return "percentage_xlarge", "率 (20%+)"
    
    # 5. 価格指数（CPI、PPI等）
    if any(x in tag_lower for x in ['cpi', 'ppi', 'price index']):
        if avg_value > 50:  # 指数は通常50以上
            return "index", "指数"
        else:
            # 変化率の場合
            if max_value < 5:
                return "percentage_small", "率 (0-5%)"
            else:
                return "percentage_medium", "率 (0-10%)"
    
    # 6. 販売・生産関連
    if any(x in tag_lower for x in ['sales', 'production', 'orders']):
        if avg_value > 1000000:
            return "millions", "百万単位"
        elif avg_value > 1000:
            return "thousands", "千単位"
        else:
            if max_value < 5:
                return "percentage_small", "率 (0-5%)"
            else:
                return "percentage_medium", "率 (0-10%)"
    
    # 7. 数値範囲による分類（より厳密）
    if avg_value > 10000000:  # 1000万以上
        return "billions", "十億単位"
    elif avg_value > 1000000:  # 100万以上
        return "millions", "百万単位"
    elif avg_value > 100000:  # 10万以上
        return "count_hundreds_k", "件数 (10万)"
    elif avg_value > 10000:  # 1万以上
        return "thousands", "千単位"
    elif avg_value > 200:  # 200以上
        return "index", "指数"
    elif avg_value > 30 and avg_value < 80 and value_range < 30:  # PMI範囲
        return "index_50", "指数 (50基準)"
    elif avg_value < 30:  # 30未満
        # スケールで細分化
        if max_value < 5:
            return "percentage_small", "率 (0-5%)"
        elif max_value < 10:
            return "percentage_medium", "率 (0-10%)"
        elif max_value < 20:
            return "percentage_large", "率 (0-20%)"
        else:
            return "percentage_xlarge", "率 (20%+)"
    else:
        return "other", "その他"

def create_currency_chart(df, currency, value_type):
    """通貨別チャート作成（動的スケールグルーピング）"""
    data = df[(df['currency'] == currency) & (df['data_tag'] != "None")]
    
    if data.empty:
        st.warning(f"{currency}のデータがありません")
        return None
    
    # 指標ごとの統計情報を収集
    indicator_stats = {}
    for tag in sorted(data['data_tag'].unique()):
        tag_data = data[data['data_tag'] == tag].copy()
        if not tag_data.empty and value_type in tag_data.columns:
            numeric_values = pd.to_numeric(tag_data[value_type], errors='coerce').dropna()
            if len(numeric_values) > 0:
                indicator_stats[tag] = {
                    'min': numeric_values.min(),
                    'max': numeric_values.max(),
                    'mean': numeric_values.mean(),
                    'range': numeric_values.max() - numeric_values.min(),
                    'data': tag_data
                }
    
    # 動的にスケールグループを作成
    scale_groups = create_dynamic_scale_groups(indicator_stats, tag)
    
    # 各スケールグループ別にチャートを作成
    return create_multi_scale_charts(data, currency, value_type, scale_groups, indicator_stats)

def create_single_axis_chart(data, currency, value_type, unit_group):
    """単軸チャート作成"""
    fig = go.Figure()
    colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel1
    
    for i, tag in enumerate(sorted(data['data_tag'].unique())):
        tag_data = data[data['data_tag'] == tag].copy()
        if not tag_data.empty:
            # 日付でソート
            tag_data = tag_data.sort_values('date')
            
            # データの前処理と補間
            cleaned_values = clean_and_interpolate_data(tag_data[value_type])
            
            # 有効なデータのみ使用
            valid_mask = ~cleaned_values.isna()
            if valid_mask.any():
                valid_data = tag_data[valid_mask]
                valid_values = cleaned_values[valid_mask]
                
                # 重要度情報を追加
                importance_info = valid_data['importance'].iloc[0] if 'importance' in valid_data.columns and len(valid_data) > 0 else 'unknown'
                importance_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(importance_info, '⚪')
                
                fig.add_trace(go.Scatter(
                    x=valid_data['date'],
                    y=valid_values,
                    mode='lines+markers',
                    name=f"{importance_emoji} {tag}",
                    line=dict(color=colors[i % len(colors)], width=2, shape='linear'),
                    marker=dict(size=4),
                    connectgaps=True,
                    hovertemplate=f'<b>{tag}</b><br>重要度: {importance_info}<br>Date: %{{x}}<br>Value: %{{y:.2f}}<br><extra></extra>'
                ))
    
    # 単位に応じた軸設定
    yaxis_title = get_yaxis_title(unit_group)
    
    fig.update_layout(
        title=f"🏛️ {currency} Economic Indicators ({value_type.capitalize()})",
        xaxis_title="📅 Date",
        yaxis_title=yaxis_title,
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', family='Arial'),
        height=700,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    
    return fig

def create_dynamic_scale_groups(indicator_stats, tag_name_for_reference):
    """動的にスケールグループを作成（バランス版）"""
    # 指標をカテゴリ別に分類
    percentage_small = []  # 0-10%程度
    percentage_large = []  # 10%以上のパーセンテージ
    pmi_indicators = []    # PMI系（50付近）
    large_numbers = []     # 100以上の大きな数値
    negative_large = []    # 大きな負の値
    
    for indicator, stats in indicator_stats.items():
        abs_max = max(abs(stats['min']), abs(stats['max']))
        
        # PMI系の判定
        if ('PMI' in indicator or 'Composite' in indicator or 'Manufacturing' in indicator or 'Services' in indicator) and 40 <= abs_max <= 70:
            pmi_indicators.append(indicator)
        # 大きな負の値（Trade Balanceなど）
        elif stats['max'] < 0 and abs_max > 50:
            negative_large.append(indicator)
        # 100以上の大きな数値
        elif abs_max >= 100:
            large_numbers.append(indicator)
        # パーセンテージ系の判定
        elif abs_max <= 50:  # 50%以下はパーセンテージとみなす
            if abs_max <= 10:
                percentage_small.append(indicator)
            else:
                percentage_large.append(indicator)
        else:
            # その他は大きな数値に
            large_numbers.append(indicator)
    
    scale_groups = []
    
    # パーセンテージ系小グループ（0-10%）
    if percentage_small:
        min_vals = [indicator_stats[ind]['min'] for ind in percentage_small]
        max_vals = [indicator_stats[ind]['max'] for ind in percentage_small]
        scale_groups.append({
            'indicators': percentage_small,
            'label': f"小パーセンテージ: {min(min_vals):.1f}~{max(max_vals):.1f}%",
            'min': min(min_vals),
            'max': max(max_vals)
        })
    
    # パーセンテージ系大グループ（10%以上）
    if percentage_large:
        min_vals = [indicator_stats[ind]['min'] for ind in percentage_large]
        max_vals = [indicator_stats[ind]['max'] for ind in percentage_large]
        scale_groups.append({
            'indicators': percentage_large,
            'label': f"大パーセンテージ: {min(min_vals):.1f}~{max(max_vals):.1f}%",
            'min': min(min_vals),
            'max': max(max_vals)
        })
    
    # PMI系
    if pmi_indicators:
        min_vals = [indicator_stats[ind]['min'] for ind in pmi_indicators]
        max_vals = [indicator_stats[ind]['max'] for ind in pmi_indicators]
        scale_groups.append({
            'indicators': pmi_indicators,
            'label': f"PMI指数: {min(min_vals):.0f}~{max(max_vals):.0f}",
            'min': min(min_vals),
            'max': max(max_vals)
        })
    
    # 大きな負の値
    if negative_large:
        min_vals = [indicator_stats[ind]['min'] for ind in negative_large]
        max_vals = [indicator_stats[ind]['max'] for ind in negative_large]
        scale_groups.append({
            'indicators': negative_large,
            'label': f"大きな負の値: {int(min(min_vals)):,}~{int(max(max_vals)):,}",
            'min': min(min_vals),
            'max': max(max_vals)
        })
    
    # 大きな数値（さらにサブグループ化）
    if large_numbers:
        # 100-1000と、1000以上に分ける
        medium_large = []
        very_large = []
        
        for ind in large_numbers:
            abs_max = max(abs(indicator_stats[ind]['min']), abs(indicator_stats[ind]['max']))
            if abs_max < 1000:
                medium_large.append(ind)
            else:
                very_large.append(ind)
        
        if medium_large:
            min_vals = [indicator_stats[ind]['min'] for ind in medium_large]
            max_vals = [indicator_stats[ind]['max'] for ind in medium_large]
            scale_groups.append({
                'indicators': medium_large,
                'label': f"中規模数値: {int(min(min_vals))}~{int(max(max_vals))}",
                'min': min(min_vals),
                'max': max(max_vals)
            })
        
        if very_large:
            min_vals = [indicator_stats[ind]['min'] for ind in very_large]
            max_vals = [indicator_stats[ind]['max'] for ind in very_large]
            scale_groups.append({
                'indicators': very_large,
                'label': f"大規模数値: {int(min(min_vals)):,}~{int(max(max_vals)):,}",
                'min': min(min_vals),
                'max': max(max_vals)
            })
    
    # スケールの小さい順にソート
    scale_groups.sort(key=lambda x: max(abs(x['min']), abs(x['max'])))
    
    return scale_groups

def create_multi_scale_charts(data, currency, value_type, scale_groups, indicator_stats):
    """スケールグループ別に複数のチャートを作成"""
    charts = []
    
    for group in scale_groups:
        if not group['indicators']:
            continue
            
        # グループごとのチャートを作成
        fig = create_scale_group_chart(data, currency, value_type, group, indicator_stats)
        if fig:
            charts.append({
                'figure': fig,
                'unit_label': group['label'],
                'indicators': group['indicators'],
                'scale_min': group['min'],
                'scale_max': group['max']
            })
    
    return charts

def create_scale_group_chart(data, currency, value_type, group, indicator_stats):
    """特定のスケールグループのチャートを作成"""
    fig = go.Figure()
    colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel1
    
    color_idx = 0
    for tag in sorted(group['indicators']):
        tag_data = data[data['data_tag'] == tag].copy()
        if not tag_data.empty:
            tag_data = tag_data.sort_values('date')
            cleaned_values = clean_and_interpolate_data(tag_data[value_type])
            valid_mask = ~cleaned_values.isna()
            
            if valid_mask.any():
                valid_data = tag_data[valid_mask]
                valid_values = cleaned_values[valid_mask]
                
                importance_info = valid_data['importance'].iloc[0] if 'importance' in valid_data.columns and len(valid_data) > 0 else 'unknown'
                importance_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(importance_info, '⚪')
                
                # 指標の統計情報を表示
                stats = indicator_stats.get(tag, {})
                hover_text = f"<b>{tag}</b><br>重要度: {importance_info}<br>範囲: {stats.get('min', 0):.2f}~{stats.get('max', 0):.2f}"
                
                fig.add_trace(go.Scatter(
                    x=valid_data['date'],
                    y=valid_values,
                    mode='lines+markers',
                    name=f"{importance_emoji} {tag}",
                    line=dict(color=colors[color_idx % len(colors)], width=2, shape='linear'),
                    marker=dict(size=4),
                    connectgaps=True,
                    hovertemplate=hover_text + "<br>Date: %{x}<br>Value: %{y:.2f}<br><extra></extra>"
                ))
                color_idx += 1
    
    # Y軸は自動スケールに任せる（固定しない）
    
    # 単位を判定
    unit_suffix = ""
    if all(indicator_stats.get(ind, {}).get('max', 0) < 100 for ind in group['indicators']):
        unit_suffix = " (%)"
    
    fig.update_layout(
        title=dict(
            text=f"🏛️ {currency} - {group['label']} ({value_type.capitalize()})",
            y=0.95,  # タイトルを少し下に
            x=0.5,
            xanchor='center'
        ),
        xaxis_title="📅 Date",
        yaxis_title=f"📊 Value{unit_suffix}",
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='#333'
        ),
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', family='Arial'),
        height=550,  # 高さを少し増やす
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,  # 凡例をグラフの下に移動
            xanchor="center",
            x=0.5
        ),
        margin=dict(t=80, b=120)  # 上下のマージンを調整
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    
    return fig

def create_multi_unit_charts(data, currency, value_type, indicator_groups):
    """単位グループ別に複数のチャートを作成"""
    charts = []
    
    # 優先順位: percentage > index_50 > index > その他
    priority_order = ["percentage", "index_50", "index", "count_thousands", "thousands", "millions", "billions", "other"]
    sorted_groups = sorted(indicator_groups.keys(), key=lambda x: priority_order.index(x) if x in priority_order else len(priority_order))
    
    for unit_group in sorted_groups:
        group_info = indicator_groups[unit_group]
        if not group_info['indicators']:
            continue
            
        # グループごとのチャートを作成
        fig = create_unit_group_chart(data, currency, value_type, unit_group, group_info)
        if fig:
            charts.append({
                'figure': fig,
                'unit_group': unit_group,
                'unit_label': group_info['label'],
                'indicators': group_info['indicators']
            })
    
    return charts

def create_unit_group_chart(data, currency, value_type, unit_group, group_info):
    """特定の単位グループのチャートを作成"""
    fig = go.Figure()
    colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel1
    
    color_idx = 0
    for tag in sorted(group_info['indicators']):
        tag_data = data[data['data_tag'] == tag].copy()
        if not tag_data.empty:
            tag_data = tag_data.sort_values('date')
            cleaned_values = clean_and_interpolate_data(tag_data[value_type])
            valid_mask = ~cleaned_values.isna()
            
            if valid_mask.any():
                valid_data = tag_data[valid_mask]
                valid_values = cleaned_values[valid_mask]
                
                importance_info = valid_data['importance'].iloc[0] if 'importance' in valid_data.columns and len(valid_data) > 0 else 'unknown'
                importance_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(importance_info, '⚪')
                
                fig.add_trace(go.Scatter(
                    x=valid_data['date'],
                    y=valid_values,
                    mode='lines+markers',
                    name=f"{importance_emoji} {tag}",
                    line=dict(color=colors[color_idx % len(colors)], width=2, shape='linear'),
                    marker=dict(size=4),
                    connectgaps=True,
                    hovertemplate=f'<b>{tag}</b><br>重要度: {importance_info}<br>Date: %{{x}}<br>Value: %{{y:.2f}}<br><extra></extra>'
                ))
                color_idx += 1
    
    # 単位に応じた軸設定
    yaxis_title = get_yaxis_title(unit_group)
    yaxis_config = get_yaxis_config(unit_group)
    
    # スケール情報を含むタイトルを作成
    scale_info = ""
    if unit_group.startswith("percentage_"):
        if "small" in unit_group:
            scale_info = " (0-5%スケール)"
        elif "medium" in unit_group:
            scale_info = " (0-10%スケール)"
        elif "large" in unit_group and "xlarge" not in unit_group:
            scale_info = " (0-20%スケール)"
        elif "xlarge" in unit_group:
            scale_info = " (20%+スケール)"
    
    fig.update_layout(
        title=f"🏛️ {currency} - {group_info['label']}{scale_info} ({value_type.capitalize()})",
        xaxis_title="📅 Date",
        yaxis_title=yaxis_title,
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', family='Arial'),
        height=500,  # 少し低めに設定
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        **yaxis_config
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    
    return fig

def create_dual_axis_chart(data, currency, value_type, indicator_groups):
    """デュアル軸チャート作成"""
    fig = go.Figure()
    colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel1
    
    # 主要グループと副グループを決定（より適切な優先順位）
    group_keys = list(indicator_groups.keys())
    
    # 優先順位: percentage > index_50 > index > その他
    priority_order = ["percentage", "index_50", "index", "count_thousands", "thousands", "millions", "billions", "other"]
    sorted_groups = sorted(group_keys, key=lambda x: priority_order.index(x) if x in priority_order else len(priority_order))
    
    primary_group = sorted_groups[0]
    secondary_group = sorted_groups[1] if len(sorted_groups) > 1 else sorted_groups[0]
    
    # 色のインデックス
    color_idx = 0
    
    # 第1軸のデータ
    for tag in indicator_groups[primary_group]['indicators']:
        tag_data = data[data['data_tag'] == tag].copy()
        if not tag_data.empty:
            tag_data = tag_data.sort_values('date')
            cleaned_values = clean_and_interpolate_data(tag_data[value_type])
            valid_mask = ~cleaned_values.isna()
            
            if valid_mask.any():
                valid_data = tag_data[valid_mask]
                valid_values = cleaned_values[valid_mask]
                
                importance_info = valid_data['importance'].iloc[0] if 'importance' in valid_data.columns and len(valid_data) > 0 else 'unknown'
                importance_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(importance_info, '⚪')
                
                fig.add_trace(go.Scatter(
                    x=valid_data['date'],
                    y=valid_values,
                    mode='lines+markers',
                    name=f"{importance_emoji} {tag}",
                    line=dict(color=colors[color_idx % len(colors)], width=2, shape='linear'),
                    marker=dict(size=4),
                    connectgaps=True,
                    yaxis='y',
                    hovertemplate=f'<b>{tag}</b><br>重要度: {importance_info}<br>Date: %{{x}}<br>Value: %{{y:.2f}}<br><extra></extra>'
                ))
                color_idx += 1
    
    # 第2軸のデータ
    for tag in indicator_groups[secondary_group]['indicators']:
        if tag in indicator_groups[primary_group]['indicators']:
            continue  # 既に追加済み
            
        tag_data = data[data['data_tag'] == tag].copy()
        if not tag_data.empty:
            tag_data = tag_data.sort_values('date')
            cleaned_values = clean_and_interpolate_data(tag_data[value_type])
            valid_mask = ~cleaned_values.isna()
            
            if valid_mask.any():
                valid_data = tag_data[valid_mask]
                valid_values = cleaned_values[valid_mask]
                
                importance_info = valid_data['importance'].iloc[0] if 'importance' in valid_data.columns and len(valid_data) > 0 else 'unknown'
                importance_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(importance_info, '⚪')
                
                fig.add_trace(go.Scatter(
                    x=valid_data['date'],
                    y=valid_values,
                    mode='lines+markers',
                    name=f"{importance_emoji} {tag} (右軸)",
                    line=dict(color=colors[color_idx % len(colors)], width=2, shape='linear', dash='dash'),
                    marker=dict(size=4, symbol='diamond'),
                    connectgaps=True,
                    yaxis='y2',
                    hovertemplate=f'<b>{tag}</b><br>重要度: {importance_info}<br>Date: %{{x}}<br>Value: %{{y:.2f}}<br><extra></extra>'
                ))
                color_idx += 1
    
    # デュアル軸レイアウト
    fig.update_layout(
        title=f"🏛️ {currency} Economic Indicators - Multi-Scale ({value_type.capitalize()})",
        xaxis_title="📅 Date",
        yaxis=dict(
            title=f"📊 {indicator_groups[primary_group]['label']}",
            side="left",
            showgrid=True,
            gridwidth=1,
            gridcolor='#333'
        ),
        yaxis2=dict(
            title=f"📈 {indicator_groups[secondary_group]['label']}",
            side="right",
            overlaying="y",
            showgrid=False
        ),
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', family='Arial'),
        height=700,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    
    return fig

def get_yaxis_title(unit_group):
    """単位グループに応じたY軸タイトルを取得"""
    titles = {
        "percentage": "📊 率 (%)",
        "percentage_small": "📊 率 (0-5%)",
        "percentage_medium": "📊 率 (0-10%)",
        "percentage_large": "📊 率 (0-20%)",
        "percentage_xlarge": "📊 率 (20%+)",
        "percentage_interest": "📊 金利 (%)",
        "percentage_unemployment": "📊 失業率 (%)",
        "percentage_inflation": "📊 インフレ率 (%)",
        "percentage_inflation_neg": "📊 インフレ率 (%)",
        "index": "📈 指数",
        "index_50": "📊 PMI/指数 (50基準)",
        "billions": "📈 十億単位",
        "millions": "📈 百万単位",
        "count_hundreds_k": "📊 件数 (10万)",
        "count_thousands": "📊 件数 (千)",
        "thousands": "📊 千単位",
        "count_units": "📊 件数",
        "other": "📊 値"
    }
    return titles.get(unit_group, "📊 値")

def create_indicator_chart(df, indicator, value_type):
    """指標別チャート作成（統一スケール）"""
    data = df[df['data_tag'] == indicator]
    
    if data.empty:
        st.warning(f"{indicator}のデータがありません")
        return None
    
    # 指標の単位を判定（サンプルデータから）
    sample_values = data[value_type].head(50)
    unit_group, unit_label = get_indicator_unit_group(indicator, sample_values)
    
    fig = go.Figure()
    colors = px.colors.qualitative.Set2 + px.colors.qualitative.Dark2
    
    for i, currency in enumerate(sorted([str(c) for c in data['currency'].dropna().unique()])):
        currency_data = data[data['currency'] == currency].copy()
        if not currency_data.empty:
            # 日付でソート
            currency_data = currency_data.sort_values('date')
            
            # データの前処理と補間
            cleaned_values = clean_and_interpolate_data(currency_data[value_type])
            
            # 有効なデータのみ使用
            valid_mask = ~cleaned_values.isna()
            if valid_mask.any():
                valid_data = currency_data[valid_mask]
                valid_values = cleaned_values[valid_mask]
                
                # 重要度情報を追加
                importance_info = valid_data['importance'].iloc[0] if 'importance' in valid_data.columns and len(valid_data) > 0 else 'unknown'
                importance_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(importance_info, '⚪')
                
                fig.add_trace(go.Scatter(
                    x=valid_data['date'],
                    y=valid_values,
                    mode='lines+markers',
                    name=f"{importance_emoji} {currency}",
                    line=dict(color=colors[i % len(colors)], width=3, shape='linear'),
                    marker=dict(size=5),
                    connectgaps=True,  # ギャップを接続
                    hovertemplate=f'<b>{currency}</b><br>重要度: {importance_info}<br>Date: %{{x}}<br>Value: %{{y:.2f}}<br><extra></extra>'
                ))
    
    # 単位に応じたY軸タイトル
    yaxis_title = get_yaxis_title(unit_group)
    
    # 単位グループ別の軸設定
    yaxis_config = get_yaxis_config(unit_group)
    
    fig.update_layout(
        title=dict(
            text=f"📊 {indicator} Cross-Currency Comparison ({value_type.capitalize()})",
            y=0.95,
            x=0.5,
            xanchor='center'
        ),
        xaxis_title="📅 Date",
        yaxis_title=yaxis_title,
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', family='Arial'),
        height=750,  # 高さを少し増やす
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        margin=dict(t=80, b=120),
        **yaxis_config
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333')
    
    return fig

def get_yaxis_config(unit_group):
    """単位グループに応じたY軸設定を取得"""
    base_config = {
        "yaxis": dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='#333'
        )
    }
    
    # パーセンテージ系の設定（範囲固定はしない）
    if unit_group.startswith("percentage"):
        config = base_config.copy()
        config["yaxis"]["ticksuffix"] = "%"
        return config
    
    elif unit_group == "index_50":
        return {
            "yaxis": dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='#333'
            ),
            "shapes": [
                dict(
                    type="line",
                    x0=0, x1=1,
                    y0=50, y1=50,
                    xref="paper",
                    line=dict(color="orange", width=1, dash="dash")
                )
            ]
        }
    elif unit_group in ["count_thousands", "thousands", "count_units"]:
        return {
            "yaxis": dict(
                tickformat=",",
                showgrid=True,
                gridwidth=1,
                gridcolor='#333'
            )
        }
    elif unit_group in ["count_hundreds_k"]:
        return {
            "yaxis": dict(
                tickformat=".1f",
                ticksuffix="万",
                showgrid=True,
                gridwidth=1,
                gridcolor='#333'
            )
        }
    elif unit_group in ["millions", "billions"]:
        return {
            "yaxis": dict(
                tickformat=".2s",  # Scientific notation
                showgrid=True,
                gridwidth=1,
                gridcolor='#333'
            )
        }
    else:
        return base_config

def get_indicators_in_all_currencies(df):
    """全通貨で揃っている経済指標を取得（類似指標含む）"""
    # 利用可能な通貨を取得
    all_currencies = sorted([str(c) for c in df['currency'].dropna().unique()])
    
    # 類似指標のマッピング（比較可能とみなす指標群）
    similar_indicators = {
        'CPI': ['CPI (YoY)', 'National CPI (YoY)', 'Core CPI (YoY)'],
        'CPI_MoM': ['CPI (MoM)', 'National CPI (MoM)', 'Core CPI (MoM)'],
        'Tokyo_CPI': ['Tokyo CPI (YoY)', 'CPI (YoY)'],  # 東京CPIと全国CPIは比較可能
        'Building_Permits': ['Building Permits', 'Housing Starts'],  # 建設関連
        'Factory_Orders': ['Factory Orders', 'Industrial Production (MoM)', 'Industrial Production (YoY)'],  # 製造業関連
        'Housing_Prices': ['Housing Prices (MoM)', 'Housing Prices (YoY)'],
        'PPI': ['PPI (MoM)', 'PPI (YoY)'],  # 生産者物価
        'Retail_Sales': ['Retail Sales (MoM)', 'Retail Sales (YoY)']
    }
    
    # 指標ごとにどの通貨で利用可能かを確認
    indicator_currency_map = {}
    for indicator in df['data_tag'].unique():
        if indicator != "None":
            indicator_currencies = set(df[df['data_tag'] == indicator]['currency'].dropna().unique())
            indicator_currency_map[indicator] = indicator_currencies
    
    # 類似指標グループで通貨カバレッジをチェック
    group_coverage = {}
    for group_name, indicators in similar_indicators.items():
        covered_currencies = set()
        for indicator in indicators:
            if indicator in indicator_currency_map:
                covered_currencies.update(indicator_currency_map[indicator])
        
        if len(covered_currencies) == len(all_currencies):
            # このグループは全通貨をカバーしている
            for indicator in indicators:
                if indicator in indicator_currency_map:
                    group_coverage[indicator] = covered_currencies
    
    # 完全一致の指標も追加
    exact_match_indicators = []
    for indicator, currencies in indicator_currency_map.items():
        if len(currencies) == len(all_currencies):
            exact_match_indicators.append(indicator)
    
    # 類似指標と完全一致指標を統合
    full_coverage_indicators = list(set(exact_match_indicators + list(group_coverage.keys())))
    
    return sorted(full_coverage_indicators), all_currencies

def main():
    # メインタイトル
    st.markdown('<h1 class="main-header">📊 Economic Data Dashboard</h1>', unsafe_allow_html=True)
    
    # データ更新チェック
    update_data_file()
    
    # データロード
    with st.spinner('📥 データを読み込み中...'):
        df = load_data()
    
    if df.empty:
        st.error("❌ データの読み込みに失敗しました")
        return
    
    # 5通貨フルカバレッジ指標の情報
    full_coverage_indicators, all_currencies = get_indicators_in_all_currencies(df)
    
    # データ統計（豊富な情報表示）
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("📋 総データ数", f"{len(df):,}")
    with col2:
        st.metric("🏛️ 通貨数", len(df['currency'].unique()))
    with col3:
        st.metric("📊 経済指標数", len([tag for tag in df['data_tag'].unique() if tag != "None"]))
    with col4:
        st.metric("🌐 全通貨指標", len(full_coverage_indicators))
    with col5:
        st.metric("📅 データ期間", f"{df['date'].min().year} - {df['date'].max().year}")
    with col6:
        # ファイル更新時刻を表示
        data_file = "./data/economic_data.csv"
        if os.path.exists(data_file):
            file_time = datetime.fromtimestamp(os.path.getmtime(data_file))
            st.metric("🔄 ファイル更新", f"{file_time.strftime('%m-%d %H:%M')}")
        else:
            st.metric("🔄 ファイル更新", "未取得")
    
    # 重要度分布を表示
    if 'importance' in df.columns:
        st.markdown("### 🎯 重要度分布")
        importance_counts = df['importance'].value_counts()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            high_count = importance_counts.get('high', 0)
            st.metric("🔴 高重要度", f"{high_count:,}件")
        with col2:
            medium_count = importance_counts.get('medium', 0)
            st.metric("🟡 中重要度", f"{medium_count:,}件")
        with col3:
            low_count = importance_counts.get('low', 0)
            st.metric("🟢 低重要度", f"{low_count:,}件")
    
    # 利用可能な指標の一覧表示
    with st.expander("📋 利用可能な経済指標一覧"):
        indicators = sorted([tag for tag in df['data_tag'].unique() if tag != "None"])
        indicator_counts = df[df['data_tag'] != "None"]['data_tag'].value_counts()
        
        cols = st.columns(3)
        for i, indicator in enumerate(indicators):
            with cols[i % 3]:
                st.write(f"• **{indicator}**: {indicator_counts.get(indicator, 0):,} records")
    
    # データ処理に関する説明
    with st.expander("🔧 データ処理について"):
        st.markdown("""
        **📈 グラフの滑らかさ改善:**
        - **異常な0値の検出**: 前後の値と比較して異常な0値を自動検出
        - **前の値で穴埋め**: 欠損値を前の値で補完（Forward Fill）
        - **線形補間**: 残った欠損値は線形補間で滑らかに接続
        - **ギャップ接続**: `connectgaps=True`でデータの断絶を自然に接続
        
        **🎯 効果:**
        - 折れ線グラフの不自然な0への急降下を防止
        - データの連続性を保持してトレンドを明確に表示
        - より見やすく分析しやすいグラフを実現
        """)
    
    # 単位・スケール分析情報
    with st.expander("📏 単位・スケール分析について"):
        st.markdown("""
        **📊 インテリジェント軸管理:**
        - **自動単位検出**: 指標名と数値範囲から最適な単位を自動判定
        - **デュアル軸表示**: 異なるスケールの指標を左右軸で分離表示
        - **適切な数値フォーマット**: 各単位に応じた見やすい表示形式
        
        **🔧 対応単位タイプ:**
        - 📊 **率 (%)**: 金利、失業率、インフレ率など（%表示）
        - 📈 **指数**: CPI、PPI等の価格指数（そのまま表示）
        - 📊 **PMI (50基準)**: 製造業・サービス業PMI（50基準線付き）
        - 📊 **件数 (千)**: 雇用統計、請求件数（千単位・カンマ区切り）
        - 📈 **大規模数値**: GDP、貿易収支（科学記法表示）
        
        **💡 デュアル軸の活用:**
        - 左軸（実線）: 主要指標グループ
        - 右軸（破線・ダイヤモンド）: 異なるスケールの指標
        - 視覚的区別で比較分析を効率化
        """)
    
    # スケール分析結果の表示
    if not df.empty:
        with st.expander("🔍 現在のデータのスケール分析"):
            scale_analysis = {}
            sample_size = min(1000, len(df))
            sample_df = df.sample(n=sample_size) if len(df) > sample_size else df
            
            for tag in sample_df['data_tag'].unique():
                if tag != "None":
                    tag_data = sample_df[sample_df['data_tag'] == tag]
                    if not tag_data.empty:
                        for value_type in ['actual', 'forecast']:
                            if value_type in tag_data.columns:
                                sample_values = tag_data[value_type].head(20)
                                unit_group, unit_label = get_indicator_unit_group(tag, sample_values)
                                
                                if unit_group not in scale_analysis:
                                    scale_analysis[unit_group] = {'label': unit_label, 'indicators': set()}
                                scale_analysis[unit_group]['indicators'].add(tag)
            
            for unit_group, info in scale_analysis.items():
                st.write(f"**{info['label']}**: {len(info['indicators'])}種類")
                indicators_list = sorted(list(info['indicators']))[:5]  # 最初の5つを表示
                for indicator in indicators_list:
                    st.write(f"  • {indicator}")
                if len(info['indicators']) > 5:
                    st.write(f"  • ... 他{len(info['indicators']) - 5}種類")
    
    st.markdown("---")
    
    # サイドバー
    st.sidebar.title("⚙️ ダッシュボード設定")
    
    # データ更新ボタン
    if st.sidebar.button("🔄 最新データ取得", help="最新の経済データを手動で取得します"):
        with st.spinner("🔄 最新データを取得中..."):
            # キャッシュをクリアして強制更新
            load_data.clear()
            # ファイルのタイムスタンプを古くして強制更新
            data_file = "./data/economic_data.csv"
            if os.path.exists(data_file):
                old_time = time.time() - (7 * 60 * 60)  # 7時間前に設定
                os.utime(data_file, (old_time, old_time))
            update_data_file()
            st.rerun()  # ページをリフレッシュ
    
    # タブ選択
    analysis_type = st.sidebar.radio(
        "📈 分析タイプを選択:",
        ["🏛️ 通貨別分析", "📊 指標別比較", "📅 経済指標カレンダー", "🌏 国別経済指標一覧"],
        index=0
    )
    
    # データタイプ選択
    value_type = st.sidebar.selectbox(
        "📊 データタイプ:",
        ["forecast", "actual"],
        format_func=lambda x: "🔮 予測値 (Forecast)" if x == "forecast" else "📈 実際値 (Actual)"
    )
    
    # 重要度フィルター
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 重要度フィルター")
    
    # 利用可能な重要度を取得
    available_importance = sorted([str(i) for i in df['importance'].dropna().unique()]) if 'importance' in df.columns else []
    
    if available_importance:
        importance_mapping = {
            'high': '🔴 高 (High)',
            'medium': '🟡 中 (Medium)', 
            'low': '🟢 低 (Low)'
        }
        
        # 重要度の選択（デフォルトはhighのみ）
        default_importance = ['high'] if 'high' in available_importance else (['High'] if 'High' in available_importance else available_importance)
        selected_importance = st.sidebar.multiselect(
            "表示する重要度:",
            available_importance,
            default=default_importance,
            format_func=lambda x: importance_mapping.get(x, x)
        )
        
        # 重要度でフィルター
        if selected_importance:
            df = df[df['importance'].isin(selected_importance)]
        else:
            st.sidebar.warning("⚠️ 重要度を少なくとも1つ選択してください")
            df = df[df['importance'].isin(available_importance)]  # 全て表示
    else:
        st.sidebar.info("📊 重要度情報が利用できません")
    
    # 5通貨フィルター
    st.sidebar.markdown("---")
    st.sidebar.subheader("🌐 全通貨フィルター")
    
    show_full_coverage_only = st.sidebar.checkbox(
        f"全{len(all_currencies)}通貨で利用可能な指標のみ表示",
        value=False,
        help=f"{len(full_coverage_indicators)}種類の指標が全{len(all_currencies)}通貨で利用可能です"
    )
    
    # フィルターを適用
    if show_full_coverage_only:
        df = df[df['data_tag'].isin(full_coverage_indicators)]
    
    if analysis_type == "🏛️ 通貨別分析":
        # 通貨選択
        currencies = sorted([str(c) for c in df['currency'].dropna().unique()])
        selected_currency = st.sidebar.selectbox(
            "🏛️ 通貨を選択:",
            currencies,
            index=currencies.index('USD') if 'USD' in currencies else 0
        )
        
        st.subheader(f"🏛️ {selected_currency} Economic Analysis")
        
        # 通貨の詳細情報
        currency_data = df[df['currency'] == selected_currency]
        currency_indicators = sorted([str(tag) for tag in currency_data['data_tag'].dropna().unique() if str(tag) != "None"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"📊 **利用可能な指標**: {len(currency_indicators)}")
        with col2:
            st.info(f"📅 **データ件数**: {len(currency_data[currency_data['data_tag'] != 'None']):,}")
        
        # チャート作成
        charts = create_currency_chart(df, selected_currency, value_type)
        if charts:
            # 単位分析結果を表示
            if len(charts) > 1:
                st.info(f"📏 **マルチスケール表示**: {len(charts)}種類のスケールグループに分けて表示")
            else:
                st.info(f"📊 **統一スケール**: {charts[0]['unit_label']}")
            
            # タブまたはエキスパンダーで複数チャートを表示
            if len(charts) > 1:
                # タブで表示
                tab_names = [f"{chart['unit_label']} ({len(chart['indicators'])}指標)" for chart in charts]
                tabs = st.tabs(tab_names)
                
                for tab, chart_info in zip(tabs, charts):
                    with tab:
                        # 各タブ内に指標リストを表示
                        with st.expander("📊 含まれる指標", expanded=False):
                            indicators_text = "、".join(chart_info['indicators'])
                            st.write(indicators_text)
                        
                        # チャートを表示
                        st.plotly_chart(chart_info['figure'], use_container_width=True)
            else:
                # 単一チャートの場合はそのまま表示
                st.plotly_chart(charts[0]['figure'], use_container_width=True)
            
            # データテーブル（デフォルトで表示）
            st.subheader("📋 データテーブル")
            table_data = df[(df['currency'] == selected_currency) & (df['data_tag'] != "None")]
            if not table_data.empty:
                # フィルター機能
                selected_indicators = st.multiselect(
                    "表示する指標を選択:",
                    currency_indicators,
                    default=currency_indicators[:5]  # デフォルトで5つ表示
                )
                
                if selected_indicators:
                    filtered_table = table_data[table_data['data_tag'].isin(selected_indicators)]
                    # 最新50件のデータを表示
                    recent_data = filtered_table.sort_values('date', ascending=False).head(50)
                    
                    # 重要度カラムを含める
                    display_columns = ['date', 'importance', 'event', 'data_tag', 'actual', 'forecast', 'previous']
                    available_columns = [col for col in display_columns if col in recent_data.columns]
                    
                    st.dataframe(
                        recent_data[available_columns],
                        use_container_width=True,
                        height=500
                    )
                    
                    # 追加のデータ詳細を展開可能セクションで
                    with st.expander("🔍 詳細フィルターとデータ"):
                        # 日付フィルター
                        col1, col2 = st.columns(2)
                        with col1:
                            start_date = st.date_input(
                                "開始日",
                                value=filtered_table['date'].min().date() if not filtered_table.empty else None
                            )
                        with col2:
                            end_date = st.date_input(
                                "終了日", 
                                value=filtered_table['date'].max().date() if not filtered_table.empty else None
                            )
                        
                        # 日付でフィルター
                        if start_date and end_date:
                            date_filtered = filtered_table[
                                (filtered_table['date'].dt.date >= start_date) & 
                                (filtered_table['date'].dt.date <= end_date)
                            ]
                            
                            st.write(f"📅 期間内のデータ: {len(date_filtered)}件")
                            if not date_filtered.empty:
                                # 重要度カラムを含める
                                detail_columns = ['date', 'importance', 'event', 'data_tag', 'actual', 'forecast', 'previous']
                                available_detail_columns = [col for col in detail_columns if col in date_filtered.columns]
                                
                                st.dataframe(
                                    date_filtered[available_detail_columns].sort_values('date', ascending=False),
                                    use_container_width=True,
                                    height=400
                                )
                else:
                    st.info("指標を選択してデータを表示してください")
            else:
                st.warning(f"{selected_currency}のデータがありません")
    
    elif analysis_type == "📊 指標別比較":  # 指標別比較
        # 指標選択
        indicators = sorted([tag for tag in df['data_tag'].unique() if tag != "None"])
        selected_indicator = st.sidebar.selectbox(
            "📊 経済指標を選択:",
            indicators,
            index=indicators.index('CPI') if 'CPI' in indicators else 0
        )
        
        st.subheader(f"📊 {selected_indicator} Cross-Currency Comparison")
        
        # 指標の詳細情報
        indicator_data = df[df['data_tag'] == selected_indicator]
        indicator_currencies = sorted([str(c) for c in indicator_data['currency'].dropna().unique()])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"🏛️ **対象通貨**: {len(indicator_currencies)}")
        with col2:
            st.info(f"📅 **データ件数**: {len(indicator_data):,}")
        with col3:
            # 指標の単位情報を表示
            if not indicator_data.empty and value_type in indicator_data.columns:
                sample_values = indicator_data[value_type].head(50)
                unit_group, unit_label = get_indicator_unit_group(selected_indicator, sample_values)
                st.info(f"📏 **単位**: {unit_label}")
        
        # チャート作成
        fig = create_indicator_chart(df, selected_indicator, value_type)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            # データテーブル（デフォルトで表示）
            st.subheader("📋 データテーブル")
            table_data = df[df['data_tag'] == selected_indicator]
            if not table_data.empty:
                # 通貨フィルター
                selected_currencies = st.multiselect(
                    "表示する通貨を選択:",
                    indicator_currencies,
                    default=indicator_currencies[:5]  # デフォルトで5つ表示
                )
                
                if selected_currencies:
                    filtered_table = table_data[table_data['currency'].isin(selected_currencies)]
                    # 最新50件のデータを表示
                    recent_data = filtered_table.sort_values('date', ascending=False).head(50)
                    
                    # 重要度カラムを含める
                    display_columns_indicator = ['date', 'currency', 'importance', 'event', 'actual', 'forecast', 'previous']
                    available_columns_indicator = [col for col in display_columns_indicator if col in recent_data.columns]
                    
                    st.dataframe(
                        recent_data[available_columns_indicator],
                        use_container_width=True,
                        height=500
                    )
                    
                    # 追加のデータ詳細を展開可能セクションで
                    with st.expander("🔍 詳細フィルターとデータ"):
                        # 日付フィルター
                        col1, col2 = st.columns(2)
                        with col1:
                            start_date = st.date_input(
                                "開始日",
                                value=filtered_table['date'].min().date() if not filtered_table.empty else None,
                                key="indicator_start_date"
                            )
                        with col2:
                            end_date = st.date_input(
                                "終了日", 
                                value=filtered_table['date'].max().date() if not filtered_table.empty else None,
                                key="indicator_end_date"
                            )
                        
                        # 日付でフィルター
                        if start_date and end_date:
                            date_filtered = filtered_table[
                                (filtered_table['date'].dt.date >= start_date) & 
                                (filtered_table['date'].dt.date <= end_date)
                            ]
                            
                            st.write(f"📅 期間内のデータ: {len(date_filtered)}件")
                            if not date_filtered.empty:
                                # 重要度カラムを含める
                                detail_columns_indicator = ['date', 'currency', 'importance', 'event', 'actual', 'forecast', 'previous']
                                available_detail_indicator = [col for col in detail_columns_indicator if col in date_filtered.columns]
                                
                                st.dataframe(
                                    date_filtered[available_detail_indicator].sort_values('date', ascending=False),
                                    use_container_width=True,
                                    height=400
                                )
                else:
                    st.info("通貨を選択してデータを表示してください")
            else:
                st.warning(f"{selected_indicator}のデータがありません")
    
    elif analysis_type == "📅 経済指標カレンダー":
        # 経済指標カレンダー機能
        st.subheader("📅 経済指標カレンダー")
        
        # 日付範囲選択
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "開始日",
                value=datetime.now() - timedelta(days=7),
                help="表示する開始日を選択"
            )
        with col2:
            end_date = st.date_input(
                "終了日", 
                value=datetime.now() + timedelta(days=30),  # 1ヶ月先まで
                help="表示する終了日を選択"
            )
        
        # 重要度フィルター（通貨フィルターは削除）
        selected_importance = st.multiselect(
            "⭐ 重要度を選択:",
            options=['High', 'Medium', 'Low'],
            default=['High', 'Medium'],
            help="表示する重要度を選択"
        )
        
        if selected_importance and start_date <= end_date:
            # 直接investpyからカレンダーデータを取得
            try:
                with st.spinner("📅 カレンダーデータを取得中..."):
                    from_date = start_date.strftime('%d/%m/%Y')
                    to_date = end_date.strftime('%d/%m/%Y')
                    
                    calendar_data = investpy.economic_calendar(
                        time_zone=None,
                        countries=['united states', 'euro zone', 'united kingdom', 'japan', 'australia'],
                        from_date=from_date,
                        to_date=to_date
                    )
                    
                    if not calendar_data.empty:
                        # データの内容をデバッグ表示
                        st.info(f"📊 取得データ: {len(calendar_data)}件")
                        if 'importance' in calendar_data.columns:
                            importance_counts = calendar_data['importance'].value_counts()
                            st.info(f"重要度別件数: {dict(importance_counts)}")
                        
                        # 通貨マッピング
                        currency_mapping = {
                            'united states': 'USD',
                            'euro zone': 'EUR', 
                            'united kingdom': 'GBP',
                            'japan': 'JPY',
                            'australia': 'AUD'
                        }
                        
                        # zone列をcurrencyに変換
                        if 'zone' in calendar_data.columns:
                            calendar_data['currency_display'] = calendar_data['zone'].map(currency_mapping).fillna(calendar_data['zone'])
                        else:
                            calendar_data['currency_display'] = calendar_data.get('currency', 'Unknown')
                        
                        # 重要度でフィルター（大文字小文字を統一）
                        if 'importance' in calendar_data.columns:
                            # 重要度の値を正規化
                            calendar_data['importance_normalized'] = calendar_data['importance'].str.strip().str.title()
                            selected_importance_normalized = [imp.strip().title() for imp in selected_importance]
                            calendar_filtered = calendar_data[calendar_data['importance_normalized'].isin(selected_importance_normalized)].copy()
                        else:
                            st.warning("重要度列が見つかりません")
                            calendar_filtered = calendar_data.copy()
                        
                        if not calendar_filtered.empty:
                            st.info(f"🎯 フィルター後: {len(calendar_filtered)}件")
                            
                            # 重要度による色分け
                            importance_colors = {
                                'High': '🔴',
                                'Medium': '🟡', 
                                'Low': '🟢'
                            }
                            
                            # 日付変換
                            calendar_filtered['date_parsed'] = pd.to_datetime(calendar_filtered['date'], dayfirst=True, errors='coerce')
                            calendar_filtered = calendar_filtered.dropna(subset=['date_parsed'])
                            calendar_filtered['date_str'] = calendar_filtered['date_parsed'].dt.strftime('%Y-%m-%d')
                            
                            # 日付ごとにグループ化
                            grouped = calendar_filtered.groupby('date_str')
                            
                            for date_str, group in grouped:
                                with st.expander(f"📅 {date_str} ({len(group)}件)", expanded=True):
                                    # 重要度順にソート
                                    importance_order = {'High': 0, 'Medium': 1, 'Low': 2}
                                    group['importance_rank'] = group['importance'].map(importance_order).fillna(3)
                                    group_sorted = group.sort_values(['importance_rank', 'time'])
                                    
                                    for _, row in group_sorted.iterrows():
                                        # 正規化された重要度を使用
                                        importance_display = row.get('importance_normalized', row.get('importance', ''))
                                        importance_icon = importance_colors.get(importance_display, '⚪')
                                        
                                        # 時間情報を取得
                                        time_info = row.get('time', '')
                                        if pd.notna(time_info) and str(time_info) != '':
                                            time_display = f"⏰ {time_info}"
                                        else:
                                            time_display = ""
                                        
                                        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 4, 2])
                                        with col1:
                                            st.write(f"{importance_icon}")
                                        with col2:
                                            st.write(f"**{row['currency_display']}**")
                                        with col3:
                                            st.write(time_display)
                                        with col4:
                                            st.write(f"{row['event']}")
                                        with col5:
                                            if pd.notna(row.get('actual')) and str(row.get('actual')) != '':
                                                st.write(f"実績: **{row['actual']}**")
                                            elif pd.notna(row.get('forecast')) and str(row.get('forecast')) != '':
                                                st.write(f"予測: {row['forecast']}")
                                            else:
                                                st.write("--")
                        else:
                            st.info("選択された重要度のデータがありません")
                    else:
                        st.warning("指定期間にカレンダーデータがありません")
                        
            except Exception as e:
                st.error(f"カレンダーデータ取得エラー: {e}")
        else:
            st.warning("重要度を選択し、正しい日付範囲を設定してください")
    
    elif analysis_type == "🌏 国別経済指標一覧":
        # 国別経済指標ヒストリカル一覧
        st.subheader("🌏 国別経済指標ヒストリカル一覧")
        
        # 国選択
        country_mapping = {
            'USD': '🇺🇸 アメリカ',
            'EUR': '🇪🇺 ユーロ圏', 
            'GBP': '🇬🇧 イギリス',
            'JPY': '🇯🇵 日本',
            'AUD': '🇦🇺 オーストラリア'
        }
        
        available_currencies = sorted([str(c) for c in df['currency'].dropna().unique()])
        selected_country = st.selectbox(
            "🏛️ 国を選択:",
            options=available_currencies,
            format_func=lambda x: country_mapping.get(x, x),
            help="表示する国を選択してください"
        )
        
        if selected_country:
            # 選択された国のデータを取得
            country_data = df[df['currency'] == selected_country].copy()
            
            if not country_data.empty:
                # 直近2年分のデータを取得
                country_data['year'] = pd.to_datetime(country_data['date']).dt.year
                available_years = sorted(country_data['year'].dropna().unique(), reverse=True)
                
                # 直近2年を自動選択
                recent_years = available_years[:2] if len(available_years) >= 2 else available_years
                
                col1, col2 = st.columns(2)
                with col1:
                    # データタイプ選択（actualまたはforecast）
                    data_type = st.selectbox(
                        "📊 データタイプ:",
                        options=['actual', 'forecast'],
                        format_func=lambda x: "📈 実績値" if x == "actual" else "🔮 予測値"
                    )
                with col2:
                    st.info(f"📅 表示期間: {min(recent_years)}年 - {max(recent_years)}年")
                
                # 直近2年のデータを取得
                year_data = country_data[country_data['year'].isin(recent_years)].copy()
                
                if not year_data.empty:
                    # 年月とイベントでピボットテーブル作成
                    year_data['year_month'] = pd.to_datetime(year_data['date']).dt.strftime('%Y年%m月')
                    
                    # 経済指標の日本語変換マッピング
                    indicator_japanese = {
                        'Unemployment Rate': '失業率',
                        'Employment Rate': '雇用率', 
                        'Initial Jobless Claims': '新規失業保険申請件数',
                        'Continuing Jobless Claims': '継続失業保険申請件数',
                        'CPI (YoY)': '消費者物価指数(前年比)',
                        'CPI (MoM)': '消費者物価指数(前月比)',
                        'Core CPI (YoY)': 'コア消費者物価指数(前年比)',
                        'Core CPI (MoM)': 'コア消費者物価指数(前月比)',
                        'National CPI (YoY)': '全国消費者物価指数(前年比)',
                        'National CPI (MoM)': '全国消費者物価指数(前月比)',
                        'Tokyo CPI (YoY)': '東京消費者物価指数(前年比)',
                        'Tokyo CPI (MoM)': '東京消費者物価指数(前月比)',
                        'PPI (YoY)': '生産者物価指数(前年比)',
                        'PPI (MoM)': '生産者物価指数(前月比)',
                        'GDP (QoQ)': 'GDP(前期比)',
                        'GDP (YoY)': 'GDP(前年比)',
                        'Current Account': '経常収支',
                        'Trade Balance': '貿易収支',
                        'PMI Manufacturing': '製造業PMI',
                        'PMI Services': 'サービス業PMI',
                        'Industrial Production (YoY)': '鉱工業生産指数(前年比)',
                        'Industrial Production (MoM)': '鉱工業生産指数(前月比)',
                        'Factory Orders': '工場受注',
                        'Building Permits': '建設許可件数',
                        'Housing Starts': '住宅着工件数',
                        'Interest Rate': '政策金利',
                        'Retail Sales (YoY)': '小売売上高(前年比)',
                        'Retail Sales (MoM)': '小売売上高(前月比)',
                        'Housing Prices (YoY)': '住宅価格指数(前年比)',
                        'Housing Prices (MoM)': '住宅価格指数(前月比)',
                        'Consumer Confidence': '消費者信頼感指数'
                    }
                    
                    # 経済指標をカテゴリ別に分類
                    indicator_categories = {
                        '👥 雇用関連': ['Unemployment Rate', 'Employment Rate', 'Initial Jobless Claims', 'Continuing Jobless Claims'],
                        '💰 物価関連': ['CPI (YoY)', 'CPI (MoM)', 'Core CPI (YoY)', 'Core CPI (MoM)', 'National CPI (YoY)', 'National CPI (MoM)', 'Tokyo CPI (YoY)', 'Tokyo CPI (MoM)', 'PPI (YoY)', 'PPI (MoM)'],
                        '📈 景気関連': ['GDP (QoQ)', 'GDP (YoY)', 'Current Account', 'Trade Balance', 'PMI Manufacturing', 'PMI Services'],
                        '🏭 製造業関連': ['Industrial Production (YoY)', 'Industrial Production (MoM)', 'Factory Orders', 'Building Permits', 'Housing Starts'],
                        '🏦 政策金利': ['Interest Rate'],
                        '🛒 消費関連': ['Retail Sales (YoY)', 'Retail Sales (MoM)', 'Housing Prices (YoY)', 'Housing Prices (MoM)', 'Consumer Confidence']
                    }
                    
                    # 全指標リスト
                    all_major_indicators = []
                    for indicators in indicator_categories.values():
                        all_major_indicators.extend(indicators)
                    
                    # データタグが主要指標に含まれるデータを抽出
                    filtered_data = year_data[year_data['data_tag'].isin(all_major_indicators)].copy()
                    
                    if not filtered_data.empty:
                        # ピボットテーブル作成
                        try:
                            pivot_table = filtered_data.pivot_table(
                                index='year_month',
                                columns='data_tag',
                                values=data_type,
                                aggfunc='last'  # 最新の値を使用
                            )
                            
                            # 年月順に並び替え
                            all_periods = sorted(pivot_table.index)
                            
                            # データが存在する指標のみ表示
                            available_indicators = [col for col in pivot_table.columns if not pivot_table[col].isna().all()]
                            
                            if available_indicators:
                                st.subheader(f"{country_mapping.get(selected_country, selected_country)} - 直近2年間 経済指標一覧")
                                
                                # 統計情報表示
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("📊 指標数", len(available_indicators))
                                with col2:
                                    st.metric("📅 データ期間", f"{min(recent_years)}-{max(recent_years)}年")
                                with col3:
                                    total_data_points = pivot_table[available_indicators].notna().sum().sum()
                                    st.metric("📈 データポイント", total_data_points)
                                
                                # 縦軸にカテゴリ・指標、横軸に月のテーブル作成
                                structured_data = []
                                
                                for category_name, indicators in indicator_categories.items():
                                    # そのカテゴリの指標で利用可能なもの
                                    category_indicators = [ind for ind in indicators if ind in available_indicators]
                                    
                                    if category_indicators:
                                        # カテゴリヘッダー行を追加
                                        category_row = {'ジャンル': category_name, '指標名': ''}
                                        for month in pivot_table.index:
                                            category_row[month] = ''
                                        structured_data.append(category_row)
                                        
                                        # 各指標の行を追加
                                        for indicator in category_indicators:
                                            # 日本語名を取得、なければ英語名をそのまま使用
                                            japanese_name = indicator_japanese.get(indicator, indicator)
                                            indicator_row = {'ジャンル': '', '指標名': japanese_name}
                                            for month in pivot_table.index:
                                                value = pivot_table.loc[month, indicator] if month in pivot_table.index else None
                                                if pd.notna(value) and isinstance(value, (int, float)):
                                                    indicator_row[month] = f"{value:.2f}"
                                                else:
                                                    indicator_row[month] = "--"
                                            structured_data.append(indicator_row)
                                
                                # DataFrameに変換
                                if structured_data:
                                    structured_df = pd.DataFrame(structured_data)
                                    
                                    # インデックスを設定
                                    structured_df = structured_df.set_index(['ジャンル', '指標名'])
                                    
                                    # 数値データの変化に基づいてスタイリング関数を定義
                                    def color_changes(val):
                                        if val == "--" or val == "":
                                            return 'background-color: #f0f0f0'  # グレー（データなし）
                                        return ''
                                    
                                    def highlight_dataframe(df):
                                        # 各行（指標）について前月比での色分け
                                        styled_df = df.copy()
                                        
                                        for idx in df.index:
                                            if df.loc[idx].name[1] != '':  # 指標名が空でない行のみ処理
                                                row_values = []
                                                for col in df.columns:
                                                    val = df.loc[idx, col]
                                                    if val != "--" and val != "":
                                                        try:
                                                            row_values.append((col, float(val)))
                                                        except:
                                                            row_values.append((col, None))
                                                    else:
                                                        row_values.append((col, None))
                                                
                                                # 前月比での色分け
                                                for i, (col, current_val) in enumerate(row_values):
                                                    if current_val is not None and i > 0:
                                                        prev_val = row_values[i-1][1]
                                                        if prev_val is not None:
                                                            if current_val > prev_val:
                                                                styled_df.loc[idx, col] = f'<span style="background-color: rgba(255, 200, 200, 0.5)">{df.loc[idx, col]}</span>'
                                                            elif current_val < prev_val:
                                                                styled_df.loc[idx, col] = f'<span style="background-color: rgba(200, 255, 200, 0.5)">{df.loc[idx, col]}</span>'
                                                            else:
                                                                styled_df.loc[idx, col] = f'<span style="background-color: rgba(240, 240, 240, 0.5)">{df.loc[idx, col]}</span>'
                                        
                                        return styled_df
                                    
                                    # スタイル適用
                                    try:
                                        def style_row(row):
                                            styles = []
                                            for i in range(len(row)):
                                                if row.iloc[i] == '--' or row.iloc[i] == '':
                                                    styles.append('background-color: rgba(240, 240, 240, 0.3)')
                                                else:
                                                    try:
                                                        current_val = float(row.iloc[i])
                                                        
                                                        # 前の有効な値を遡って検索
                                                        prev_val = None
                                                        for j in range(i-1, -1, -1):
                                                            if row.iloc[j] != '--' and row.iloc[j] != '':
                                                                try:
                                                                    prev_val = float(row.iloc[j])
                                                                    break
                                                                except:
                                                                    continue
                                                        
                                                        if prev_val is not None:
                                                            if current_val > prev_val:
                                                                styles.append('background-color: rgba(255, 200, 200, 0.3)')
                                                            elif current_val < prev_val:
                                                                styles.append('background-color: rgba(200, 255, 200, 0.3)')
                                                            else:
                                                                styles.append('background-color: rgba(255, 255, 200, 0.3)')
                                                        else:
                                                            styles.append('')  # 比較対象がない場合
                                                    except:
                                                        styles.append('')
                                            return styles
                                        
                                        styled_df = structured_df.style.apply(style_row, axis=1)
                                        
                                        st.dataframe(
                                            styled_df,
                                            use_container_width=True,
                                            height=min(600, len(structured_df) * 35 + 100)
                                        )
                                    except:
                                        # スタイリングに失敗した場合は通常のDataFrameを表示
                                        st.dataframe(
                                            structured_df,
                                            use_container_width=True,
                                            height=min(600, len(structured_df) * 35 + 100)
                                        )
                                    
                                    # 凡例を追加
                                    st.markdown("""
                                    **📊 色分け凡例:**
                                    - 🔴 **薄い赤**: 前月より増加
                                    - 🟢 **薄い緑**: 前月より減少  
                                    - ⚫ **グレー**: データなし
                                    """)
                                
                                # 注意書き
                                st.info("""
                                📌 **注意事項**
                                - データは investpy から取得した実際の経済指標です
                                - "--" は該当月にデータが発表されていないことを示します
                                - 数値の単位は指標により異なります（%、数値など）
                                - 将来の投資判断の参考としてご利用ください
                                """)
                                
                            else:
                                st.warning(f"{selected_year}年の主要経済指標データが見つかりません")
                        except Exception as e:
                            st.error(f"データ処理エラー: {e}")
                    else:
                        st.warning(f"{selected_year}年の主要経済指標データがありません")
                else:
                    st.warning(f"{selected_year}年のデータがありません")
            else:
                st.warning(f"{country_mapping.get(selected_country, selected_country)}のデータがありません")
    
    # フッター
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; color: #666;'>
        📊 Economic Dashboard | Built with Streamlit<br>
        🔄 Last Updated: {time.strftime('%Y-%m-%d %H:%M:%S')} | 
        💾 Data Cache: 30 minutes | 
        🟢 Status: Connected
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()