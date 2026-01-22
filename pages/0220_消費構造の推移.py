import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from app.utils import get_country_list_sorted, get_safe_default_countries 

# データのロード確認とセッションステートからの取得
if 'df_avg_spend' not in st.session_state:
    st.error("必要なデータ (df_avg_spend) がロードされていません。Homeに戻ってデータロードを確認してください。")
    # 処理続行のために空のデータフレームを設定
    df_spend = pd.DataFrame() 
else:
    df_spend = st.session_state.df_avg_spend 

# 必須の定数
ITEM_ORDER = st.session_state.get('ITEM_ORDER', [])
COLOR_MAP = st.session_state.get('COLOR_MAP', {})

def page_expense_time_series():
    st.header("観光消費構造時系列推移（国別比較）")
    
    if df_spend.empty:
        st.warning("観光消費構造の時系列データが見つかりません。データロードを確認してください。")
        return

    # データの整形
    # MultiIndexのデータをリセット
    df_ts = df_spend.reset_index().copy()
    
    # 費目関連のカラムを抽出
    ratio_columns = [col for col in df_ts.columns if col.endswith('_ratio')]
    unit_columns = [col for col in df_ts.columns if col.endswith('_unit')]
    
    # 時系列軸を作成（例: 2019-1Q, 2019-2Q, ...）
    df_ts['period'] = df_ts['year'].astype(str) + '-' + df_ts['Quarter']
    
    # 期間の選択
    available_years = sorted(df_ts['year'].unique().tolist())
    
    if not available_years:
        st.warning("有効な年データが見つかりません。")
        return

    if 'start_year_ts' not in st.session_state:
        st.session_state.start_year_ts = available_years[0]
        
    if 'end_year_ts' not in st.session_state:
        st.session_state.end_year_ts = available_years[-1]
        
    # インデックスの計算
    start_index = available_years.index(st.session_state.start_year_ts) if st.session_state.start_year_ts in available_years else 0
    end_index = available_years.index(st.session_state.end_year_ts) if st.session_state.end_year_ts in available_years else len(available_years) - 1
    
    col_start, col_end = st.columns(2)
    
    with col_start:
        start_year = st.selectbox(
            "開始年を選択",
            available_years,
            index=start_index,
            key='start_year_ts_key'
        )
        st.session_state.start_year_ts = start_year
    
    with col_end:
        end_year = st.selectbox(
            "終了年を選択", 
            available_years, 
            index=end_index,
            key='end_year_ts_key'
        )
        st.session_state.end_year_ts = end_year

    if start_year > end_year:
        st.error("エラー: 開始年は終了年より前に設定してください。")
        return
        
    st.markdown("---")
    
    # 選択された期間でデータをフィルタリング
    df_filtered_ts = df_ts[
        (df_ts['year'] >= start_year) & 
        (df_ts['year'] <= end_year)
    ]

    # 国の選択
    countries_sorted = get_country_list_sorted(df_ts) 
    
    if 'ts_country_multiselect' not in st.session_state:
        initial_default_countries = get_safe_default_countries(countries_sorted, max_list_count=9)
        st.session_state.ts_country_multiselect = initial_default_countries

    # セッション状態の国リストを更新（有効な選択肢のみを保持）
    current_selection = st.session_state.ts_country_multiselect
    valid_selection = [c for c in current_selection if c in countries_sorted]
    st.session_state.ts_country_multiselect = valid_selection # 初期値としてvalid_selectionを使用

    selected_countries = st.multiselect(
        "比較する国を選択", 
        countries_sorted,
        default=st.session_state.ts_country_multiselect,
        key='ts_country_multiselect_key'
    )
    st.session_state.ts_country_multiselect = selected_countries

    if not selected_countries:
        st.info("比較したい国を1つ以上選択してください。")
        return
        
    st.markdown("---")

    # グラフの描画
    for country in selected_countries:
        
        # 選択された国のデータのみを抽出
        df_country = df_filtered_ts[df_filtered_ts['country'] == country].sort_values('period')
        
        if df_country.empty:
            st.warning(f"{country} の {start_year}年〜{end_year}年 のデータが見つかりません。")
            continue
            
        # 費目名をクリーニングとデータ整形 (consumption_unit)
        df_unit_melt = df_country.melt(
            id_vars=['period', 'year', 'Quarter'], 
            value_vars=unit_columns, 
            var_name='費目', 
            value_name='消費単価 (円)'
        )
        df_unit_melt['費目'] = df_unit_melt['費目'].str.replace('_unit', '')
        
        # 費目名をクリーニングとデータ整形 (composition_ratio)
        df_ratio_melt = df_country.melt(
            id_vars=['period', 'year', 'Quarter'], 
            value_vars=ratio_columns, 
            var_name='費目', 
            value_name='構成比 (%)'
        )
        df_ratio_melt['費目'] = df_ratio_melt['費目'].str.replace('_ratio', '')


        col1, col2 = st.columns(2)
        
        with col1:
            # 費目別消費単価の時系列推移 (折れ線グラフ)
            fig_unit = px.line(
                df_unit_melt,
                x='period',
                y='消費単価 (円)',
                color='費目',
                line_group='費目',
                category_orders={"費目": ITEM_ORDER},
                title=f"{country}: 費目別 消費単価 の推移 (円)",
                color_discrete_map=COLOR_MAP
            )
            fig_unit.update_layout(xaxis_title="期間 (年-四半期)", legend_title="費目")
            st.plotly_chart(fig_unit, use_container_width=True)
            
        with col2:
            # 費目別構成比率の時系列推移 (折れ線グラフ)
            fig_ratio = px.line(
                df_ratio_melt,
                x='period',
                y='構成比 (%)',
                color='費目',
                line_group='費目',
                category_orders={"費目": ITEM_ORDER},
                title=f"{country}: 費目別 構成比率 の推移 (%)",
                color_discrete_map=COLOR_MAP
            )
            fig_ratio.update_layout(xaxis_title="期間 (年-四半期)", legend_title="費目", yaxis_ticksuffix="%")
            st.plotly_chart(fig_ratio, use_container_width=True)
            
        st.markdown("---") # 国ごとの区切り線
        
    # キャプション
    st.markdown(
        """
        <p style='font-size: small; color: #888888; margin-top: 20px;'>
        ※出典：観光庁「インバウンド消費動向調査」集計データ<br>
        ※データは観光庁の調査の年/四半期平均値に基づいています。
        </p>
        """,
        unsafe_allow_html=True
    )

# ページ関数を実行
if 'df_avg_spend' in st.session_state:
    page_expense_time_series()