import streamlit as st
from app.utils import load_data, get_pc_label, COLOR_MAP, ITEM_ORDER

# ============================================
# UIレイアウト (共通設定)
# ============================================
st.set_page_config(
    page_title="観光×消費 インバウンドデータ分析基盤", 
    layout="wide"
)

# ============================================
# データ読込とセッションステートへの格納
# ============================================
load_results = load_data()

# 戻り値が9つであることを確認
if load_results is None or len(load_results) != 9:
    st.stop()    
(
    df_jnto_pivot, 
    df_avg_spend, 
    df_destination_pivot, 
    df_pca_scores, 
    df_jnto_yearly, 
    df_avg_spend_yearly, 
    df_market_potential_quarterly, 
    df_market_potential_yearly, 
    all_consumption_items_ordered 
) = load_results

# 共通データとヘルパー関数をセッションステートに格納
st.session_state.df_jnto_pivot = df_jnto_pivot
st.session_state.df_avg_spend = df_avg_spend
st.session_state.df_destination_pivot = df_destination_pivot
st.session_state.df_pca_scores = df_pca_scores
st.session_state.df_jnto_yearly = df_jnto_yearly
st.session_state.df_avg_spend_yearly = df_avg_spend_yearly
st.session_state.df_market_potential_quarterly = df_market_potential_quarterly
st.session_state.df_market_potential_yearly = df_market_potential_yearly
st.session_state.all_consumption_items_ordered = all_consumption_items_ordered

st.session_state.SOURCE_CAPTION = "出典: 観光庁「訪日外国人消費動向調査」より作成"
if 'year' in df_market_potential_yearly.columns:
    st.session_state.DEFAULT_YEAR = df_market_potential_yearly['year'].max()
else:
    st.session_state.DEFAULT_YEAR = 2024 
# --------------------------------------------------

st.session_state.get_pc_label = get_pc_label
st.session_state.COLOR_MAP = COLOR_MAP
st.session_state.ITEM_ORDER = ITEM_ORDER


st.title("観光×消費 インバウンドデータ分析基盤")

st.markdown("""
    #### インバウンド市場を「戦略」「消費」「行動」の三側面から多角的に分析

    1.  **市場ポテンシャル分析 (戦略軸):**  
        各国の**訪日客数**（量）と**1人あたり消費単価**（質）をマッピングし、市場規模（ポテンシャル）を可視化します。  
        これにより、**高付加価値顧客**（LOHI: Low Visitors / High Spending）や**ボリューム顧客**（HILO: High Visitors / Low Spending）など、各国・地域の戦略的な位置づけを把握できます。

    2.  **観光消費構造分析 (消費軸):**  
        国別の費目ごと（宿泊、飲食、買物など）の消費単価と構成比と、その年次・四半期推移を国別に比較します。  
        特定の国で消費構造がどのように変化しているかを把握できます。

    3.  **旅行中の行動傾向分析 (行動軸):**  
        旅行中の行動の傾向について国ごとの違いと、その変化を可視化します。
        インバウンドのニーズや関心事の変化を捉えることができます。

    #### これらによりインバウンド施策を検討するための判断材料を提供します。
""")