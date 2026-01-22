import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from app.utils import get_country_list_sorted, get_safe_default_countries, get_pc_label

if 'df_pca_scores' not in st.session_state:
    st.error("必要なデータがロードされていません。Homeに戻ってデータロードを確認してください。")
    st.stop()

df_pca_scores = st.session_state.df_pca_scores
get_pc_label = st.session_state.get_pc_label


def page_action_trend_timeseries():
    st.header("行動傾向推移 (PCAスコアの時系列変化)")
    st.markdown("""
        選択した国・地域について、各主成分（PC）スコアが年ごとにどのように変化したかを比較できます。
        PCスコアの基準（0: 平均）からのズレの経年変化を見ることで、その国・地域の旅行スタイルや関心度のトレンドを捉えることができます。
    """)
    
    if df_pca_scores.empty or 'Year' not in df_pca_scores.columns or 'country' not in df_pca_scores.columns:
        st.warning("PCスコアデータが見つかりません。`pca_scores_timeseries.csv`を確認してください。")
        st.stop()
        
# 国の選択
    countries_sorted = get_country_list_sorted(df_pca_scores, country_col_name='country')
    
    initial_default_countries = get_safe_default_countries(countries_sorted, max_list_count=8)

    if 'pca_ts_country_multiselect' not in st.session_state:
        st.session_state.pca_ts_country_multiselect = initial_default_countries
        
    current_selection = st.session_state.pca_ts_country_multiselect
    valid_selection = [c for c in current_selection if c in countries_sorted]
    st.session_state.pca_ts_country_multiselect = valid_selection

    selected_countries = st.multiselect(
        "比較する国を選択", 
        countries_sorted,
        default=st.session_state.pca_ts_country_multiselect, 
        key='pca_ts_country_multiselect_key'
    )
    st.session_state.pca_ts_country_multiselect = selected_countries

    if not selected_countries:
        st.info("比較したい国を1つ以上選択してください。")
        st.stop()
        
    st.markdown("---")
        
# データの整形
    
    df_filtered_pca_ts = df_pca_scores[df_pca_scores['country'].isin(selected_countries)].copy()
    
    if df_filtered_pca_ts.empty:
        st.warning("選択された国のデータが見つかりません。")
        st.stop()
        
    pc_columns = [col for col in df_filtered_pca_ts.columns if col.startswith('PC')]

    df_melted_pca = df_filtered_pca_ts.melt(
        id_vars=['Year', 'country'],
        value_vars=pc_columns,
        var_name='PC軸',
        value_name='PCスコア'
    )
    
    df_melted_pca['PC軸_ラベル'] = df_melted_pca['PC軸'].apply(get_pc_label)
    
# グラフの描画
    
    pc_color_map = {
        'PC1: 日本文化への関心と体験意欲': '#1f77b4',
        'PC2: アクティブ志向 vs 和の寛ぎ・食志向': '#ff7f0e',
        'PC3: 自然・地方志向 vs 都市型娯楽志向': '#2ca02c',
    }

    for country in selected_countries:
        
        min_year = min(df_filtered_pca_ts['Year'])
        max_year = max(df_filtered_pca_ts['Year'])
        
        df_country = df_melted_pca[df_melted_pca['country'] == country]
        
        if df_country.empty:
            st.warning(f"{country} のデータが見つかりません。")
            continue
        
        fig_ts = px.line(
            df_country,
            x='Year',
            y='PCスコア',
            color='PC軸_ラベル',
            line_group='PC軸_ラベル',
            title=f"{country}: 各PCスコアの経年変化（{min_year}年〜{max_year}年）",
            labels={'PCスコア': 'PCスコア (0が平均)', 'Year': '年'},
            color_discrete_map=pc_color_map
        )
        
        fig_ts.update_xaxes(tickformat='d')
        
        fig_ts.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", annotation_text="平均 (0)", annotation_position="top right")
        
        fig_ts.update_layout(legend_title="PC軸の解釈")
        
        fig_ts.update_layout(
            annotations=[
                dict(
                    text="出典：日本政府観光局（JNTO）より作成",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=1, 
                    y=-0.20, 
                    font=dict(size=10, color="gray"),
                    align="right"
                )
            ],
            margin=dict(b=50) 
        )
        
        st.plotly_chart(fig_ts, use_container_width=True)
        
        st.markdown("---")

    # 画面下部の注釈
    st.markdown(
        """
        <p style='font-size: small; color: #888888;'>
        ※このグラフは、各PC軸のスコアが年ごとにどのように変化したかを示しています。<br>
        ※PCスコアが0から大きく離れるほど、その行動傾向（スタイル、関心度など）が全国籍・地域の平均からかけ離れていることを意味します。
        </p>
        """,
        unsafe_allow_html=True
    )

# ページ関数を実行
if 'df_pca_scores' in st.session_state:
    page_action_trend_timeseries()