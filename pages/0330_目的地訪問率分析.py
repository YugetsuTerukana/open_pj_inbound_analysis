import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

if 'df_destination_pivot' not in st.session_state:
    st.error("必要なデータ (df_destination_pivot) がロードされていません。")
    st.stop()

df_destination_pivot = st.session_state.get('df_destination_pivot', pd.DataFrame())

def page_destination_analysis():
    st.header("目的地訪問率分析（都道府県別）")
    
    if df_destination_pivot.empty:
        st.warning("目的地訪問率のデータが見つかりません。データロードを確認してください。")
        return

    # 年別 TOP/WORST N / 比較年比ランキング
    
    # 年選択ウィジェット
    all_years = sorted(df_destination_pivot.index.tolist(), reverse=True)
    
    if not all_years:
        st.warning("有効な年データがありません。")
        return

    # セッションステートの初期化とインデックスの特定
    if 'destination_year_select' not in st.session_state:
        st.session_state.destination_year_select = all_years[0]
    
    default_year_value = st.session_state.destination_year_select
    try:
        default_index = all_years.index(default_year_value)
    except ValueError:
        default_index = 0

    selected_year = st.selectbox(
        "ランキングを表示する年を選択", 
        options=all_years, 
        index=default_index
    )
    st.session_state.destination_year_select = selected_year
    
    # 選択された年のデータを取得
    try:
        # loc[selected_year] で Pandas Series (都道府県ごとの訪問率) を取得
        df_selected_year = df_destination_pivot.loc[selected_year] 
    except KeyError:
        st.warning(f"{selected_year}年のデータが見つかりませんでした。")
        return
        
    # ランキングのデータ準備 (構成比・累積率の計算)
    
    # 全都道府県の訪問率の合計を計算（分母とする）
    total_visit_rate = df_selected_year.sum()

    if total_visit_rate == 0:
        st.warning(f"{selected_year}年の全都道府県の訪問率合計がゼロです。累積率の計算をスキップします。")
        cumulative_multiplier = 0
    else:
        cumulative_multiplier = 100 / total_visit_rate
    
    # 全都道府県の構成比データフレームを作成
    if cumulative_multiplier > 0:
        df_selected_year_ratio = df_selected_year * cumulative_multiplier
        df_selected_year_ratio.name = '構成比 (%)'
    else:
        df_selected_year_ratio = df_selected_year.copy()
        df_selected_year_ratio[:] = 0
        df_selected_year_ratio.name = '構成比 (%)'

    # ----------------------------------------------------
    # TOP 10 (訪問率が高い順)
    # ----------------------------------------------------
    df_top_10 = df_selected_year.sort_values(ascending=False).head(10).reset_index()
    df_top_10.columns = ["都道府県", "訪問率 (%)"]
    
    if cumulative_multiplier > 0:
        df_top_10['構成比 (%)'] = df_top_10['訪問率 (%)'] * cumulative_multiplier
        df_top_10['累積率 (%)'] = df_top_10['構成比 (%)'].cumsum() 
    else:
        df_top_10['構成比 (%)'] = 0
        df_top_10['累積率 (%)'] = 0
        
    df_top_10 = df_top_10[["都道府県", "訪問率 (%)", "構成比 (%)", "累積率 (%)"]] 
    top_10_prefs = df_top_10['都道府県'].tolist()

    # ----------------------------------------------------
    # WORST 10 (訪問率が低い順)
    # ----------------------------------------------------
    df_worst_10 = df_selected_year.sort_values(ascending=True).head(10).reset_index()
    df_worst_10.columns = ["都道府県", "訪問率 (%)"]
    
    if cumulative_multiplier > 0:
        df_worst_10['構成比 (%)'] = df_worst_10['訪問率 (%)'] * cumulative_multiplier
        # WORST 10 の累積率は意味が薄いため、TOP 10 の累積率とは計算ロジックが異なる可能性があるが、
        # 元のコードのロジックを踏襲する
        df_worst_10['累積率 (%)'] = df_worst_10['構成比 (%)'].cumsum() 
    else:
        df_worst_10['構成比 (%)'] = 0
        df_worst_10['累積率 (%)'] = 0

    df_worst_10 = df_worst_10[["都道府県", "訪問率 (%)", "構成比 (%)", "累積率 (%)"]]
    worst_10_prefs = df_worst_10['都道府県'].tolist()
    
    # ----------------------------------------------------
    # 前年比増加率ランキングの計算 (訪問率ベース)
    # ----------------------------------------------------
    prev_year = selected_year - 1
    df_growth_top_10_prev = pd.DataFrame()
    growth_prev_10_prefs = []
    
    if prev_year in df_destination_pivot.index:
        df_prev_year = df_destination_pivot.loc[prev_year]
        diff_prev = df_selected_year - df_prev_year
        # 0割りのエラーを避けるために np.inf, -np.inf を NaN に置き換え
        growth_rate_prev = (diff_prev / df_prev_year) * 100
        growth_rate_prev = growth_rate_prev.replace([np.inf, -np.inf], np.nan)
        
        df_growth_rate_prev = pd.DataFrame({
            '都道府県': df_selected_year.index,
            '増加率 (%)': growth_rate_prev.values,
            f'{selected_year}年 (%)': df_selected_year.values,
            f'{prev_year}年 (%)': df_prev_year.values,
        })
        
        # 増加率が 0 より大きいもの (増加した都道府県) のみでランキングを作成
        df_growth_top_10_prev = df_growth_rate_prev[df_growth_rate_prev['増加率 (%)'] > 0].sort_values(by='増加率 (%)', ascending=False).head(10).reset_index(drop=True)
        growth_prev_10_prefs = df_growth_top_10_prev['都道府県'].tolist()

    # ----------------------------------------------------
    # 前年比増加率ランキングの計算 (構成比ベース)
    # ----------------------------------------------------
    df_growth_top_10_prev_ratio = pd.DataFrame()
    growth_prev_10_prefs_ratio = []

    if prev_year in df_destination_pivot.index and total_visit_rate > 0:
        # 前年の構成比を計算
        df_prev_year_data = df_destination_pivot.loc[prev_year]
        total_prev_visit_rate = df_prev_year_data.sum()
        
        if total_prev_visit_rate > 0:
            df_prev_year_ratio = df_prev_year_data * (100 / total_prev_visit_rate)
            
            # 構成比の増減率を計算
            diff_ratio_prev = df_selected_year_ratio - df_prev_year_ratio
            growth_rate_ratio_prev = (diff_ratio_prev / df_prev_year_ratio) * 100
            growth_rate_ratio_prev = growth_rate_ratio_prev.replace([np.inf, -np.inf], np.nan)
            
            df_growth_rate_prev_ratio = pd.DataFrame({
                '都道府県': df_selected_year.index,
                '増加率 (%)': growth_rate_ratio_prev.values,
                f'{selected_year}年 (%)': df_selected_year_ratio.values,  # 構成比
                f'{prev_year}年 (%)': df_prev_year_ratio.values,        # 構成比
            })
            
            # 増加率が 0 より大きいもののみでランキングを作成
            df_growth_top_10_prev_ratio = df_growth_rate_prev_ratio[df_growth_rate_prev_ratio['増加率 (%)'] > 0].sort_values(by='増加率 (%)', ascending=False).head(10).reset_index(drop=True)
            growth_prev_10_prefs_ratio = df_growth_top_10_prev_ratio['都道府県'].tolist()

    # ----------------------------------------------------
    # 2019年比増加率ランキングの計算 (訪問率ベース)
    # ----------------------------------------------------
    pre_covid_year = 2019
    df_growth_top_10_2019 = pd.DataFrame()
    growth_2019_10_prefs = []
    
    if pre_covid_year in df_destination_pivot.index and selected_year != pre_covid_year:
        df_pre_covid_year = df_destination_pivot.loc[pre_covid_year]
        diff_2019 = df_selected_year - df_pre_covid_year
        growth_rate_2019 = (diff_2019 / df_pre_covid_year) * 100
        growth_rate_2019 = growth_rate_2019.replace([np.inf, -np.inf], np.nan)
        
        df_growth_rate_2019 = pd.DataFrame({
            '都道府県': df_selected_year.index,
            '増加率 (%)': growth_rate_2019.values,
            f'{selected_year}年 (%)': df_selected_year.values,
            f'{pre_covid_year}年 (%)': df_pre_covid_year.values,
        })
        
        # 増加率が 0 より大きいもののみでランキングを作成
        df_growth_top_10_2019 = df_growth_rate_2019[df_growth_rate_2019['増加率 (%)'] > 0].sort_values(by='増加率 (%)', ascending=False).head(10).reset_index(drop=True)
        growth_2019_10_prefs = df_growth_top_10_2019['都道府県'].tolist()
        
    # ----------------------------------------------------
    # 2019年比増加率ランキングの計算 (構成比ベース)
    # ----------------------------------------------------
    df_growth_top_10_2019_ratio = pd.DataFrame()
    growth_2019_10_prefs_ratio = []

    if pre_covid_year in df_destination_pivot.index and selected_year != pre_covid_year and total_visit_rate > 0:
        # 2019年の構成比を計算
        df_2019_year_data = df_destination_pivot.loc[pre_covid_year]
        total_2019_visit_rate = df_2019_year_data.sum()
        
        if total_2019_visit_rate > 0:
            df_2019_year_ratio = df_2019_year_data * (100 / total_2019_visit_rate)
            
            # 構成比の増減率を計算
            diff_ratio_2019 = df_selected_year_ratio - df_2019_year_ratio
            growth_rate_ratio_2019 = (diff_ratio_2019 / df_2019_year_ratio) * 100
            growth_rate_ratio_2019 = growth_rate_ratio_2019.replace([np.inf, -np.inf], np.nan)
            
            df_growth_rate_2019_ratio = pd.DataFrame({
                '都道府県': df_selected_year.index,
                '増加率 (%)': growth_rate_ratio_2019.values,
                f'{selected_year}年 (%)': df_selected_year_ratio.values, # 構成比
                f'{pre_covid_year}年 (%)': df_2019_year_ratio.values,   # 構成比
            })
            
            # 増加率が 0 より大きいもののみでランキングを作成
            df_growth_top_10_2019_ratio = df_growth_rate_2019_ratio[df_growth_rate_2019_ratio['増加率 (%)'] > 0].sort_values(by='増加率 (%)', ascending=False).head(10).reset_index(drop=True)
            growth_2019_10_prefs_ratio = df_growth_top_10_2019_ratio['都道府県'].tolist()


    # ------------------------------------
    # ランキング表示 (タブ)
    # ------------------------------------
    st.subheader(f"{selected_year}年：訪問率ランキング")

    tab_top, tab_worst, tab_growth_prev, tab_growth_prev_ratio, tab_growth_2019, tab_growth_2019_ratio = st.tabs([
        "TOP 10", 
        "WORST 10", 
        f"前年比 (訪問率ベース)",
        f"前年比 (構成比ベース)", 
        f"2019年比 (訪問率ベース)",
        f"2019年比 (構成比ベース)" 
    ])

    # ------------------------------------
    # TOP 10 タブ
    # ------------------------------------
    with tab_top:
        st.markdown(f"**{selected_year}年 訪問率が高い都道府県 TOP 10**")
        col1_top, col2_top = st.columns([1, 2])
        
        with col1_top:
            st.dataframe(
                df_top_10, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "訪問率 (%)": st.column_config.NumberColumn("訪問率 (%)", format="%.2f %%"),
                    "構成比 (%)": st.column_config.NumberColumn("構成比 (%)", format="%.2f %%", help="全訪問率合計に対する割合"),
                    "累積率 (%)": st.column_config.NumberColumn("累積率 (%)", format="%.2f %%", help="全訪問率合計に対する累積割合"), 
                }
            )

        with col2_top:
            fig_bar_top = px.bar(
                df_top_10,
                x="訪問率 (%)",
                y="都道府県",
                orientation='h',
                title=f"{selected_year}年 訪日外国人訪問率 TOP 10",
                height=400
            )
            fig_bar_top.update_layout(yaxis={'categoryorder':'total ascending'}) 
            
            # 注釈は共通キャプションで対応するため、グラフ内の注釈は簡略化または削除（元のコード通りに再現）
            fig_bar_top.update_layout(margin=dict(b=50)) 
            st.plotly_chart(fig_bar_top, use_container_width=True)

    # ------------------------------------
    # WORST 10 タブ
    # ------------------------------------
    with tab_worst:
        st.markdown(f"**{selected_year}年 訪問率が低い都道府県 WORST 10**")
        col1_worst, col2_worst = st.columns([1, 2])
        
        with col1_worst:
            st.dataframe(
                df_worst_10, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "訪問率 (%)": st.column_config.NumberColumn("訪問率 (%)", format="%.2f %%"),
                    "構成比 (%)": st.column_config.NumberColumn("構成比 (%)", format="%.2f %%", help="全訪問率合計に対する割合"),
                    "累積率 (%)": st.column_config.NumberColumn("累積率 (%)", format="%.2f %%", help="全訪問率合計に対する累積割合"), 
                }
            )

        with col2_worst:
            fig_bar_worst = px.bar(
                df_worst_10,
                x="訪問率 (%)",
                y="都道府県",
                orientation='h',
                title=f"{selected_year}年 訪日外国人訪問率 WORST 10",
                height=400
            )
            fig_bar_worst.update_layout(yaxis={'categoryorder':'total descending'})
            fig_bar_worst.update_layout(margin=dict(b=50))
            st.plotly_chart(fig_bar_worst, use_container_width=True)
            
    # ------------------------------------
    # 前年比 増加率ランキング タブ (訪問率ベース)
    # ------------------------------------
    with tab_growth_prev:
        st.markdown(f"**{selected_year}年 訪問率 増加率ランキング TOP 10 (前年 {prev_year}年比)**")

        if not df_growth_top_10_prev.empty:
            col1_growth, col2_growth = st.columns([1, 2])
            
            display_columns = ['都道府県', '増加率 (%)', f'{selected_year}年 (%)', f'{prev_year}年 (%)']
            df_display = df_growth_top_10_prev[display_columns]
            
            with col1_growth:
                st.dataframe(
                    df_display,
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "増加率 (%)": st.column_config.NumberColumn("増加率 (%)", format="%.1f %%", help="前年訪問率に対する増加率"),
                        f'{selected_year}年 (%)': st.column_config.NumberColumn(f'{selected_year}年 (%)', format="%.2f %%"),
                        f'{prev_year}年 (%)': st.column_config.NumberColumn(f'{prev_year}年 (%)', format="%.2f %%"),
                    }
                )

            with col2_growth:
                fig_bar_growth = px.bar(
                    df_growth_top_10_prev,
                    x="増加率 (%)",
                    y="都道府県",
                    orientation='h',
                    title=f"{selected_year}年 訪問率 増加率 TOP 10 ({prev_year}年比)",
                    height=400
                )
                fig_bar_growth.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_bar_growth.update_layout(margin=dict(b=50))
                st.plotly_chart(fig_bar_growth, use_container_width=True)
        else:
            st.info(f"前年 ({prev_year}年) のデータが存在しないか、訪問率が上昇した都道府県がありません。")

    # ------------------------------------
    # 前年比 増加率ランキング タブ (構成比ベース)
    # ------------------------------------
    with tab_growth_prev_ratio:
        st.markdown(f"**{selected_year}年 構成比 増加率ランキング TOP 10 (前年 {prev_year}年比)**")

        if not df_growth_top_10_prev_ratio.empty:
            col1_growth_ratio, col2_growth_ratio = st.columns([1, 2])
            
            display_columns_ratio = ['都道府県', '増加率 (%)', f'{selected_year}年 (%)', f'{prev_year}年 (%)'] 
            df_display_ratio = df_growth_top_10_prev_ratio[display_columns_ratio]
            
            with col1_growth_ratio:
                st.dataframe(
                    df_display_ratio,
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "増加率 (%)": st.column_config.NumberColumn("増加率 (%)", format="%.1f %%", help="前年構成比に対する増加率"),
                        f'{selected_year}年 (%)': st.column_config.NumberColumn(f'{selected_year}年 (%)', format="%.2f %%", help=f'{selected_year}年 構成比'), 
                        f'{prev_year}年 (%)': st.column_config.NumberColumn(f'{prev_year}年 (%)', format="%.2f %%", help=f'{prev_year}年 構成比'),
                    }
                )

            with col2_growth_ratio:
                fig_bar_growth_ratio = px.bar(
                    df_growth_top_10_prev_ratio,
                    x="増加率 (%)",
                    y="都道府県",
                    orientation='h',
                    title=f"{selected_year}年 構成比 増加率 TOP 10 ({prev_year}年比)",
                    height=400
                )
                fig_bar_growth_ratio.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_bar_growth_ratio.update_layout(margin=dict(b=50))
                st.plotly_chart(fig_bar_growth_ratio, use_container_width=True)
        else:
            st.info(f"前年 ({prev_year}年) のデータが存在しないか、構成比が上昇した都道府県がありません。")


    # ------------------------------------
    # 2019年比 増加率ランキング タブ (訪問率ベース)
    # ------------------------------------
    with tab_growth_2019:
        st.markdown(f"**{selected_year}年 訪問率 増加率ランキング TOP 10 (2019年比)**")

        if selected_year == pre_covid_year:
            st.warning("2019年と2019年の比較はできません。他の年を選択してください。")
        elif not df_growth_top_10_2019.empty:
            col1_growth_2019, col2_growth_2019 = st.columns([1, 2])
            
            display_columns_2019 = ['都道府県', '増加率 (%)', f'{selected_year}年 (%)', f'{pre_covid_year}年 (%)']
            df_display_2019 = df_growth_top_10_2019[display_columns_2019]
            
            with col1_growth_2019:
                st.dataframe(
                    df_display_2019,
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "増加率 (%)": st.column_config.NumberColumn("増加率 (%)", format="%.1f %%", help="2019年訪問率に対する増加率"),
                        f'{selected_year}年 (%)': st.column_config.NumberColumn(f'{selected_year}年 (%)', format="%.2f %%"),
                        f'{pre_covid_year}年 (%)': st.column_config.NumberColumn(f'{pre_covid_year}年 (%)', format="%.2f %%"),
                    }
                )

            with col2_growth_2019:
                fig_bar_growth_2019 = px.bar(
                    df_growth_top_10_2019,
                    x="増加率 (%)",
                    y="都道府県",
                    orientation='h',
                    title=f"{selected_year}年 訪問率 増加率 TOP 10 (2019年比)",
                    height=400
                )
                fig_bar_growth_2019.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_bar_growth_2019.update_layout(margin=dict(b=50))
                st.plotly_chart(fig_bar_growth_2019, use_container_width=True)
        else:
            if selected_year != pre_covid_year:
                st.info(f"2019年 ({pre_covid_year}年) のデータが存在しないか、または訪問率が2019年を上回る都道府県がありません。")

    # ------------------------------------
    # 2019年比 増加率ランキング タブ (構成比ベース)
    # ------------------------------------
    with tab_growth_2019_ratio:
        st.markdown(f"**{selected_year}年 構成比 増加率ランキング TOP 10 (2019年比)**")

        if selected_year == pre_covid_year:
            st.warning("2019年と2019年の比較はできません。他の年を選択してください。")
        elif not df_growth_top_10_2019_ratio.empty:
            col1_growth_2019_ratio, col2_growth_2019_ratio = st.columns([1, 2])
            
            display_columns_2019_ratio = ['都道府県', '増加率 (%)', f'{selected_year}年 (%)', f'{pre_covid_year}年 (%)']
            df_display_2019_ratio = df_growth_top_10_2019_ratio[display_columns_2019_ratio]
            
            with col1_growth_2019_ratio:
                st.dataframe(
                    df_display_2019_ratio,
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "増加率 (%)": st.column_config.NumberColumn("増加率 (%)", format="%.1f %%", help="2019年構成比に対する増加率"),
                        f'{selected_year}年 (%)': st.column_config.NumberColumn(f'{selected_year}年 (%)', format="%.2f %%", help=f'{selected_year}年 構成比'),
                        f'{pre_covid_year}年 (%)': st.column_config.NumberColumn(f'{pre_covid_year}年 (%)', format="%.2f %%", help=f'{pre_covid_year}年 構成比'),
                    }
                )

            with col2_growth_2019_ratio:
                fig_bar_growth_2019_ratio = px.bar(
                    df_growth_top_10_2019_ratio,
                    x="増加率 (%)",
                    y="都道府県",
                    orientation='h',
                    title=f"{selected_year}年 構成比 増加率 TOP 10 (2019年比)",
                    height=400
                )
                fig_bar_growth_2019_ratio.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_bar_growth_2019_ratio.update_layout(margin=dict(b=50))
                st.plotly_chart(fig_bar_growth_2019_ratio, use_container_width=True)
        else:
            if selected_year != pre_covid_year:
                st.info(f"2019年 ({pre_covid_year}年) のデータが存在しないか、または構成比が2019年を上回る都道府県がありません。")

            
    st.markdown("---")
    
    # ------------------------------------
    # 経年変化比較
    # ------------------------------------
    st.subheader("経年変化比較")

    # メニュー復帰時の選択保持ロジック
    if 'selected_prefs_comparison' not in st.session_state:
        st.session_state.selected_prefs_comparison = top_10_prefs[:5] 
    
    if 'manual_prefs_multiselect' not in st.session_state:
        st.session_state.manual_prefs_multiselect = st.session_state.selected_prefs_comparison

    # 一括選択を行うためのチェックボックスとボタン
    st.markdown("##### ランキングに基づいて一括で追加")
    
    prefs_to_add = set()
    
    # チェックボックスを6つに拡張
    col_check_1, col_check_2, col_check_3, col_check_4, col_check_5, col_check_6 = st.columns([1.2, 1.2, 2, 2, 2, 2])

    with col_check_1:
        check_top10_val = st.checkbox("TOP 10", key='check_top10')
        if check_top10_val:
            prefs_to_add.update(top_10_prefs)
            
    with col_check_2:
        check_worst10_val = st.checkbox("WORST 10", key='check_worst10')
        if check_worst10_val:
            prefs_to_add.update(worst_10_prefs)

    with col_check_3:
        check_growth_prev_val = st.checkbox(f"前年比 (訪問率)", key='check_growth_prev')
        if check_growth_prev_val:
            prefs_to_add.update(growth_prev_10_prefs)
            
    with col_check_4:
        check_growth_prev_ratio_val = st.checkbox(f"前年比 (構成比)", key='check_growth_prev_ratio') 
        if check_growth_prev_ratio_val:
            prefs_to_add.update(growth_prev_10_prefs_ratio)
            
    with col_check_5:
        check_growth_2019_val = st.checkbox("2019年比 (訪問率)", key='check_growth_2019')
        if check_growth_2019_val:
            prefs_to_add.update(growth_2019_10_prefs)
            
    with col_check_6:
        check_growth_2019_ratio_val = st.checkbox("2019年比 (構成比)", key='check_growth_2019_ratio') 
        if check_growth_2019_ratio_val:
            prefs_to_add.update(growth_2019_10_prefs_ratio)

    # 既存の選択肢はマルチセレクトの現在の値
    current_selected = set(st.session_state.manual_prefs_multiselect)
    
    all_prefs_options = df_destination_pivot.columns.tolist()

    # 一括追加ボタン
    if st.button("選択したランキングの都道府県を追加"):
        # 現在の選択リストに、チェックされたランキングの都道府県を追加
        new_selection = sorted(list(current_selected.union(prefs_to_add)))
        
        st.session_state.manual_prefs_multiselect = new_selection
        st.session_state.selected_prefs_comparison = new_selection
        
        # st.rerun() を使用して変更を即座に反映
        st.rerun() 

    # 手動選択マルチセレクト
    selected_prefs = st.multiselect(
        "比較する都道府県を選択", 
        options=all_prefs_options, 
        key='manual_prefs_multiselect'
    )
    
    st.session_state.selected_prefs_comparison = selected_prefs

    if selected_prefs:
        # 選択された都道府県のデータを抽出
        df_plot = df_destination_pivot[selected_prefs]
        
        fig_line = px.line(
            df_plot,
            x=df_plot.index,
            y=selected_prefs,
            title="選択された都道府県の訪問率の経年変化",
            labels={'value': '訪問率 (%)', 'index': '年'}
        )
        
        # 出典注釈の追加
        fig_line.update_layout(
            annotations=[
                dict(
                    text="出典：日本政府観光局（JNTO）より作成",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=1, y=-0.20,
                    font=dict(size=10, color="gray"),
                    align="right"
                )
            ],
            margin=dict(b=50)
        )

        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("比較したい都道府県を選択してください。")

    st.markdown("---") 
    
    # 共通のキャプション
    st.markdown(
        """
        <p style='font-size: small; color: #888888;'>
        ※出典：日本政府観光局（JNTO）「都道府県別訪問地」データ<br>
        ※データは年次（各年の集計値）に基づいています。<br>
        ※構成比は、全訪問率の合計に対する割合を示します。
        </p>
        """,
        unsafe_allow_html=True
    )

# ページ関数を実行
if 'df_destination_pivot' in st.session_state:
    page_destination_analysis()