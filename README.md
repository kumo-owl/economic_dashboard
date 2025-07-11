# 📊 経済ダッシュボード

リアルタイム経済指標を可視化・分析するStreamlitダッシュボードアプリケーション

## 🌟 特徴

- **📈 リアルタイムデータ**: investpyを使用して最新の経済指標データを自動取得
- **🏛️ 多通貨対応**: USD、EUR、GBP、JPY、AUDの5通貨をサポート
- **📊 多様な分析機能**: 通貨別・指標別・カレンダー・国別一覧の4つの分析モード
- **🎨 視覚的分析**: 動的スケールグループ化による見やすいチャート表示
- **📅 経済カレンダー**: 将来の経済指標発表予定を時系列表示
- **🌏 国別一覧**: 直近2年間の経済指標を日本語でカテゴリ別表示

## 🚀 機能

### 1. 🏛️ 通貨別分析
- 選択した通貨の経済指標をスケール別にグループ化
- 自動的に6つのバランス良いグループに分類
- 重要度フィルター対応

### 2. 📊 指標別比較  
- 特定の経済指標を全通貨で比較
- 類似指標グループでの比較機能
- チャートとデータテーブル表示

### 3. 📅 経済指標カレンダー
- 過去1週間〜将来1ヶ月の経済指標スケジュール
- 重要度別色分け表示（🔴High、🟡Medium、🟢Low）
- 発表時間・実績値・予測値を表示

### 4. 🌏 国別経済指標一覧
- 直近2年間の経済指標を日本語で表示
- 6つのカテゴリに分類（雇用・物価・景気・製造業・政策金利・消費）
- 前月比増減を色分けで視覚化（🔴増加、🟢減少）

## 📋 必要な環境

- Python 3.9以上
- Streamlit
- pandas
- plotly
- investpy
- requests

## 🛠️ インストール

1. リポジトリをクローン:
```bash
git clone <repository-url>
cd economic_dashboard
```

2. 必要なパッケージをインストール:
```bash
pip install -r requirements.txt
```

3. アプリケーションを起動:
```bash
streamlit run dashboard.py
```

## 📊 データソース

- **investpy**: 経済指標の取得
- **対象国**: アメリカ、ユーロ圏、イギリス、日本、オーストラリア
- **更新頻度**: 6時間ごとの自動キャッシュ更新
- **データ期間**: 過去5年分 + 将来1ヶ月分

## 📈 サポートする経済指標

### 👥 雇用関連
- 失業率、雇用率、新規失業保険申請件数

### 💰 物価関連  
- 消費者物価指数(CPI)、コアCPI、生産者物価指数(PPI)
- 前年比・前月比・地域別(東京CPI等)

### 📈 景気関連
- GDP、経常収支、貿易収支、PMI

### 🏭 製造業関連
- 鉱工業生産指数、工場受注、建設許可件数

### 🏦 政策金利
- 各国中央銀行政策金利

### 🛒 消費関連
- 小売売上高、住宅価格指数、消費者信頼感指数

## 🎨 UI機能

- **ダークテーマ**: 見やすい暗いテーマ
- **レスポンシブデザイン**: 様々な画面サイズに対応
- **インタラクティブチャート**: Plotlyによる高機能グラフ
- **カラーコーディング**: データの増減を直感的に把握

## ⚠️ 注意事項

- データはinvestpyから取得した実際の経済指標です
- 投資判断の参考情報として提供され、将来の結果を保証するものではありません
- API制限により、過度なデータ取得は制限される場合があります

## 🔧 設定

### キャッシュ設定
- データキャッシュ: 30分間
- ファイル更新間隔: 6時間

### カスタマイズ
`dashboard.py`内の以下の設定を変更可能:
- 対象通貨の追加/削除
- データ更新間隔
- チャート色設定
- 指標カテゴリの編集

## 📞 サポート

バグ報告や機能要望は、GitHubのIssuesページまでお願いします。

---

**Built with Streamlit 🚀 | Powered by investpy 📊**