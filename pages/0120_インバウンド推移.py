import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np 
from app.utils import get_country_list_sorted_for_inbound, get_safe_default_countries, calculate_delta, format_delta_abs, format_delta_percent 

if 'df_jnto_pivot' not in st.session_state:
    st.error("必要なデータがロードされていません。Homeに戻ってデータロードを確認してください。")
    st.stop()

df_jnto = st.session_state.df_jnto_pivot

def page_inbound_trend():
    st.header("インバウンド推移（複数国・月別比較）")
    
    all_countries = df_jnto.columns.tolist()
    all_countries_sorted = get_country_list_sorted_for_inbound(all_countries)
    all_dates = df_jnto.index.tolist()
    
    if 'inbound_countries_multiselect' not in st.session_state:
        initial_default_countries = get_safe_default_countries(all_countries_sorted, max_list_count=9)
        st.session_state.inbound_countries_multiselect = initial_default_countries
        
    current_selection = st.session_state.inbound_countries_multiselect
    valid_selection = [c for c in current_selection if c in all_countries_sorted]
    st.session_state.inbound_countries_multiselect = valid_selection

    selected_countries = st.multiselect(
        "比較する国を選択",
        all_countries_sorted, 
        default=st.session_state.inbound_countries_multiselect, 
        key='inbound_countries_multiselect_key'
    )
    st.session_state.inbound_countries_multiselect = selected_countries

    if not selected_countries:
        st.info("表示したい国を1つ以上選択してください。")
        # st.stop() は関数を完全に停止させるため、ここでは return で処理を中断させます
        return
        
    # 折れ線グラフの表示
    st.subheader("訪日観光客数 時系列推移 (人)")
    
    df_plot = df_jnto[selected_countries]

    fig = px.line(
        df_plot, 
        title="訪日観光者数推移（国別比較）",
        labels={'value': '訪日観光者数 (人)', 'date': '年月', 'variable': '国'}
    )
    # 

    fig.update_yaxes(tickformat=',d')

    fig = fig.update_layout(
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
        margin=dict(b=10) 
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")

    # メトリックの表示
    st.subheader("目的月の選択と各種比較")
    
    target_options_desc = [d.strftime('%Y年%m月') for d in all_dates][::-1]
    default_index = 0
    selected_target_str = st.selectbox(
        "比較したい目的の年月を選択", 
        options=target_options_desc, 
        index=default_index, 
        key='target_date_select'
    )
    selected_target_date = pd.to_datetime(selected_target_str, format='%Y年%m月')

    try:
        target_index_loc = df_jnto.index.get_loc(selected_target_date)
    except KeyError:
        st.error("データフレームに選択された年月が含まれていません。")
        return
    
    try:
        target_series = df_jnto.loc[selected_target_date]
        prev_series = df_jnto.iloc[target_index_loc - 1] if target_index_loc > 0 else None
        yoy_date = selected_target_date - pd.DateOffset(years=1)
        yoy_series = df_jnto.loc[yoy_date] if yoy_date in df_jnto.index else None
        pre19_date = selected_target_date.replace(year=2019)
        pre19_series = df_jnto.loc[pre19_date] if pre19_date in df_jnto.index else None
    except KeyError as e:
        st.error(f"データ取得エラー: {e}")
        return
        
    # 比較用日付文字列の準備
    prev_date_str = df_jnto.index[target_index_loc - 1].strftime('%Y年%m月') if prev_series is not None and target_index_loc > 0 else 'データなし'
    
    for country in selected_countries:
        st.markdown(f"""
            <h5 style='margin-bottom: 0.5rem; margin-top: 1.5rem;'>{country}</h5>
        """, unsafe_allow_html=True)
        
        col_target, col_prev, col_yoy, col_pre19 = st.columns([3, 3, 3, 3])
        
        target_value = target_series.get(country, 0)
        
        prev_value_raw = prev_series.get(country) if prev_series is not None and country in prev_series.index else None
        prev_value = prev_value_raw if prev_value_raw is not None and not np.isnan(prev_value_raw) else None
        
        yoy_value_raw = yoy_series.get(country) if yoy_series is not None and country in yoy_series.index else None
        yoy_value = yoy_value_raw if yoy_value_raw is not None and not np.isnan(yoy_value_raw) else None
        
        pre19_value_raw = pre19_series.get(country) if pre19_series is not None and country in pre19_series.index else None
        pre19_value = pre19_value_raw if pre19_value_raw is not None and not np.isnan(pre19_value_raw) else None
        
        diff_prev, rate_prev = calculate_delta(target_value, prev_value)
        diff_yoy, rate_yoy = calculate_delta(target_value, yoy_value)
        diff_pre19, rate_pre19 = calculate_delta(target_value, pre19_value)
        
        with col_target:
            st.metric(
                f"実績 ({selected_target_str})", 
                f"{target_value:,.0f} 人", 
                label_visibility="visible"
            )
        
        with col_prev:
            st.metric(
                "前月比", 
                format_delta_abs(diff_prev, prev_value),
                delta=format_delta_percent(rate_prev),
                help=f"前月 ({df_jnto.index[target_index_loc - 1].strftime('%Y年%m月') if target_index_loc > 0 else 'データなし'}) の実績: {prev_value:,.0f} 人" if prev_value is not None else "前月データなし"
            )
        
        with col_yoy:
            st.metric(
                f"前年同月比", 
                format_delta_abs(diff_yoy, yoy_value),
                delta=format_delta_percent(rate_yoy),
                help=f"前年同月 ({yoy_date.strftime('%Y年%m月') if yoy_date in df_jnto.index else 'データなし'}) の実績: {yoy_value:,.0f} 人" if yoy_value is not None else "前年同月データなし"
            )
            
        with col_pre19:
            st.metric(
                f"2019年同月比", 
                format_delta_abs(diff_pre19, pre19_value),
                delta=format_delta_percent(rate_pre19),
                help=f"2019年同月 ({pre19_date.strftime('%Y年%m月') if pre19_date in df_jnto.index else 'データなし'}) の実績: {pre19_value:,.0f} 人" if pre19_value is not None else "2019年同月データなし"
            )
            
        # 国ごとの区切りを短くするために、margin(上下左右) を適用
        st.markdown(
            "<hr style='margin: 10px 0px 10px 0px; border-top: 1px solid #eee;'>", 
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <p style='font-size: small; color: #888888;'>
        ※グラフおよびメトリックは、日本政府観光局（JNTO）が公開している月別の国・地域ごとの訪日外客数データに基づいています。
        </p>
        """,
        unsafe_allow_html=True
    )

# ページ関数を実行
if 'df_jnto_pivot' in st.session_state:
    page_inbound_trend()