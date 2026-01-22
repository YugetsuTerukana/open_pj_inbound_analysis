import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np 
# app.utils から必要な関数をインポート
from app.utils import get_country_list_sorted, get_safe_default_countries 

# データのロード確認とセッションステートからの取得
if 'df_avg_spend' not in st.session_state:
    st.error("必要なデータ (df_avg_spend) がロードされていません。Homeに戻ってデータロードを確認してください。")
    df_spend = pd.DataFrame() 
else:
    df_spend = st.session_state.df_avg_spend 

# 必須の定数
ITEM_ORDER = st.session_state.get('ITEM_ORDER', [])
COLOR_MAP = st.session_state.get('COLOR_MAP', {})

def page_expense_ratio_analysis():
    st.header("観光消費構造（年別・複数国・四半期別比較）")
    
    if df_spend.empty:
        st.warning("観光消費構造のデータが見つかりません。データロードを確認してください。")
        return

    # 選択肢の準備

    # 年の選択肢を降順で取得
    available_years = df_spend.index.get_level_values('year').unique().sort_values(ascending=False).tolist()
    latest_year = available_years[0] if available_years else None
    
    # 四半期の選択肢を取得
    available_quarters = df_spend.index.get_level_values('Quarter').unique().sort_values().tolist()
    quarter_options = ['すべて'] + available_quarters
    
    if not latest_year:
        st.warning("有効な年データが見つかりません。")
        return

    # 年と四半期の選択（状態保持ロジックを含む）
    
    # 状態の初期化
    if 'selected_year_stable' not in st.session_state:
        st.session_state.selected_year_stable = latest_year
    if 'selected_quarters_stable' not in st.session_state:
        st.session_state.selected_quarters_stable = ['すべて']
        
    # 選択年がデータに含まれない場合のフォールバック
    if st.session_state.selected_year_stable not in available_years:
        st.session_state.selected_year_stable = latest_year

    col_y, col_q = st.columns(2)
    
    with col_y:
        try:
            default_year_index = available_years.index(st.session_state.selected_year_stable)
        except ValueError:
            default_year_index = 0
            
        selected_year = st.selectbox(
            "年を選択", 
            available_years,
            index=default_year_index,
            key='year_select_key',
        )
        st.session_state.selected_year_stable = selected_year

    with col_q:
        selected_quarters = st.multiselect(
            "四半期を選択（複数選択可）", 
            quarter_options,
            default=st.session_state.selected_quarters_stable,
            key='quarter_select_key',
        )
        st.session_state.selected_quarters_stable = selected_quarters

    st.markdown("---")
    
    # 国の選択
    
    # 選択された年のデータのみを基に国リストを取得
    countries_sorted = get_country_list_sorted(
        df_spend.loc[selected_year] if selected_year in df_spend.index.get_level_values('year') else df_spend
    )
    
    # 状態の初期化
    if 'country_multiselect_stable' not in st.session_state:
        initial_default_countries = get_safe_default_countries(countries_sorted, max_list_count=9)
        st.session_state.country_multiselect_stable = initial_default_countries

    # 選択肢の検証と更新
    current_selection = st.session_state.country_multiselect_stable
    valid_selection = [c for c in current_selection if c in countries_sorted]
    st.session_state.country_multiselect_stable = valid_selection
    
    selected_countries = st.multiselect(
        "比較する国を選択", 
        countries_sorted,
        default=st.session_state.country_multiselect_stable,
        key='country_multiselect_key'
    )
    st.session_state.country_multiselect_stable = selected_countries

    if not selected_countries or not selected_quarters:
        st.info("比較したい国と期間を1つ以上選択してください。")
        return
        
    # 表示期間の確定
    display_periods = []
    if 'すべて' in selected_quarters:
        display_periods.append('年全体集計')
    
    for q in available_quarters:
        if q in selected_quarters:
            display_periods.append(q)

    if not display_periods:
        st.warning("表示する期間が選択されていません。四半期を一つ以上選択するか、「すべて」を選択してください。")
        return
        
    # グラフの表示
    
    display_combinations = []
    for country in selected_countries:
        for period in display_periods:
            display_combinations.append((country, period))

    N = len(display_combinations)
    num_cols = min(N, 4) # 最大4列表示
    
    for j in range(0, N, num_cols):
        cols = st.columns(num_cols)
        
        for i in range(num_cols):
            index = j + i
            if index < N:
                country, period_key = display_combinations[index]
                
                unique_key = f"pie_chart_{country}_{period_key}_{selected_year}" 
                
                with cols[i]:
                    
                    if period_key == '年全体集計':
                        period_display = ""
                        is_annual_summary = True
                    else:
                        period_display = f" {period_key}"
                        is_annual_summary = False
                    
                    st.subheader(f"{selected_year}年{period_display}")
                    st.subheader(country)
                    
                    try:
                        # データのスライス（年/国/四半期）
                        if is_annual_summary:
                            # 年全体（全四半期）の平均/合計を計算
                            data_slice = df_spend.loc[(selected_year, country, slice(None))]
                            
                            ratio_columns = [col for col in data_slice.columns if col.endswith('_ratio')]
                            consumption_ratios = data_slice[ratio_columns].mean() # 構成比は平均
                            
                            unit_columns = [col for col in data_slice.columns if col.endswith('_unit')]
                            consumption_units = data_slice[unit_columns].sum() # 消費単価は合計
                            
                            avg_total_spend_official = data_slice['avg_total_spend_official'].mean() # 総消費単価は平均
                            
                        else:
                            # 特定四半期のデータを取得
                            data_slice = df_spend.loc[(selected_year, country, period_key)]
                            
                            # Seriesの場合、インデックスからカラムを取得
                            ratio_columns = [col for col in data_slice.index if col.endswith('_ratio')]
                            unit_columns = [col for col in data_slice.index if col.endswith('_unit')]
                            
                            consumption_ratios = data_slice[ratio_columns]
                            consumption_units = data_slice[unit_columns]

                            avg_total_spend_official = data_slice.get('avg_total_spend_official', 0)
                            
                    except KeyError:
                        st.error("データなし")
                        continue
                        
                    total_unit_sum = consumption_units.sum()
                    
                    # 総消費単価の表示値の決定ロジック
                    if country == "全国籍･地域" or is_annual_summary:
                        display_spend_value = avg_total_spend_official
                    else:
                        display_spend_value = total_unit_sum


                    # Pieチャートデータ整形
                    # ITEM_ORDERの順序に確実に合わせる
                    ratio_cols_ordered = [c + '_ratio' for c in ITEM_ORDER if c + '_ratio' in consumption_ratios.index]

                    # Pieチャート用のデータフレームを作成 
                    df_pie = pd.DataFrame({
                        '費目': [col.replace('_ratio', '') for col in ratio_cols_ordered], 
                        '構成比 (%)': consumption_ratios[ratio_cols_ordered].values 
                    })
                    
                    # カテゴリカル型で費目の順序を固定
                    df_pie['費目'] = pd.Categorical(df_pie['費目'], categories=ITEM_ORDER, ordered=True)
                    df_pie = df_pie.sort_values('費目').dropna(subset=['費目'])
                    
                    # メトリックの表示部分
                    st.markdown(f"<h4>総消費単価</h4>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size: small; margin-bottom: 0px;'>※1人あたりの消費額の合計</p>", unsafe_allow_html=True)
                    st.markdown(f"### ¥ {display_spend_value:,.0f}")
                    
                    # Pieチャートの描画 
                    fig_pie = px.pie(
                        df_pie, 
                        values='構成比 (%)', 
                        names='費目', 
                        title=f"{country} の消費構造",
                        hole=.3,
                        height=350,
                        color='費目',
                        color_discrete_map=COLOR_MAP
                    )
                    
                    # 費目順序を固定して表示
                    fig_pie.update_traces(
                        sort=False,
                        direction='clockwise', 
                        rotation=190 
                    ) 
                    
                    st.plotly_chart(fig_pie, use_container_width=True, key=unique_key)
    
    # 注釈
    st.markdown(
        """
        <p style='font-size: small; color: #888888; margin-top: 20px;'>
        ※出典：観光庁「インバウンド消費動向調査」集計データ。<br>
        ※データは観光庁の調査の年/四半期平均値に基づいています。<br><br>
        ※構成比（円グラフ）：四半期選択で「すべて」を選んだ場合は、選択年における全四半期の平均構成比をさらに平均しています。<br>
        ※総消費単価（メトリック）：<br>
        ・「すべて」選択時、または「全国籍・地域」の場合は、選択年における全四半期の公式平均総消費単価をさらに平均しています。<br>
        ・その他の国・地域で「すべて」選択時以外の場合は、当該期間の費目別平均単価の合計を表示しています。
        </p>
        """,
        unsafe_allow_html=True
    )

# ページ関数を実行
if 'df_avg_spend' in st.session_state:
    page_expense_ratio_analysis()