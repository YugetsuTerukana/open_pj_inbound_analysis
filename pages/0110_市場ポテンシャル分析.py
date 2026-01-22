import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from itertools import product 
from app.utils import get_country_list_sorted, get_safe_default_countries

# セッションステートからデータを取得
if 'df_market_potential_yearly' not in st.session_state:
    st.error("必要なデータがロードされていません。Homeに戻ってデータロードを確認してください。")
    st.stop()

# 必要なデータをセッションステートから取得
df_market_potential_yearly = st.session_state.df_market_potential_yearly
df_market_potential_quarterly = st.session_state.df_market_potential_quarterly

ALL_CONSUMPTION_ITEMS_ORDERED = st.session_state.all_consumption_items_ordered

# 費目/細目リストの再構築
ALL_SPEND_COLUMNS = [col for col in df_market_potential_yearly.columns if col not in ['year', 'country', 'Annual_Visitors', 'Market_Potential_Total', 'Avg_Total_Spend', 'Quarter', 'Quarterly_Visitors']]
MAJOR_ITEMS_ORDERED = [item for item in ALL_CONSUMPTION_ITEMS_ORDERED if '[全体]' in item] 

POTENTIAL_ITEMS_DICT = {
    '費目別': ['全体'] + MAJOR_ITEMS_ORDERED, 
    '細目別': ['全体'] + ALL_CONSUMPTION_ITEMS_ORDERED 
}

def page_market_potential_analysis():
    st.header("市場ポテンシャル分析")
    st.markdown("""
        各国の**年間/四半期訪日客数**（X軸）と**消費単価（1人あたりの消費額）**（Y軸）をマッピングし、
        バブルの大きさ（面積）で**市場ポテンシャル**（訪日客数 × 消費単価）を表現します。
        
        Y軸の消費単価を「費目別（大分類）」または「細目別（小分類）」で切り替えることで、詳細な潜在市場を把握できます。
    """)

    # 分析レベル設定
    
    col_level_1, col_level_2 = st.columns(2)
    
    analysis_level_options = ("年次 (年間総計)", "四半期別")
    
    if 'potential_analysis_level_state' not in st.session_state:
        st.session_state.potential_analysis_level_state = "年次 (年間総計)"
    
    try:
        level_default_index = analysis_level_options.index(st.session_state.potential_analysis_level_state)
    except ValueError:
        level_default_index = 0 
    
    with col_level_1:
        analysis_level = st.radio(
            "分析期間の単位",
            analysis_level_options,
            index=level_default_index, 
            key="potential_analysis_level_key",
            horizontal=True
        )
        st.session_state.potential_analysis_level_state = analysis_level 

    item_category_options = ("費目別", "細目別")
    
    if 'potential_item_category_state' not in st.session_state:
        st.session_state.potential_item_category_state = "費目別"

    try:
        item_category_default_index = item_category_options.index(st.session_state.potential_item_category_state)
    except ValueError:
        default_index = 0 
        
    with col_level_2:
        item_category = st.radio(
            "消費単価の分析単位",
            item_category_options,
            index=item_category_default_index, 
            key="potential_item_category_key",
            horizontal=True
        )
        st.session_state.potential_analysis_level_state = item_category 

    # 使用データと軸の設定 ---
    if analysis_level == "年次 (年間総計)":
        df_market_potential_base = df_market_potential_yearly.copy()
        visitors_col = 'Annual_Visitors'
        visitors_label = '年間訪日客数 (人) [対数]'
        title_suffix = '年次'
        # 時系列グラフのベースデータは年次データ全体
        df_time_series_base_all = df_market_potential_yearly.copy()
        df_time_series_base_all['Time_Index'] = df_time_series_base_all['year'].astype(str)
        
    else: # 四半期別
        df_market_potential_base = df_market_potential_quarterly.copy()
        visitors_col = 'Quarterly_Visitors'
        visitors_label = '四半期訪日客数 (人) [対数]'
        title_suffix = '四半期別'
        # 時系列グラフのベースデータは四半期データ全体
        df_time_series_base_all = df_market_potential_quarterly.copy()
        df_time_series_base_all['Time_Index'] = df_time_series_base_all['year'].astype(str) + '-' + df_time_series_base_all['Quarter']


    if df_market_potential_base.empty:
        st.warning("ポテンシャル分析に必要なデータが不足しています。データファイルの内容を確認してください。")
        st.stop()
        
    df_market_potential_base = df_market_potential_base[df_market_potential_base['country'] != '全国籍･地域'].copy()
    df_time_series_base_all = df_time_series_base_all[df_time_series_base_all['country'] != '全国籍･地域'].copy()
    
    # 期間/費目/国選択 UI
    
    col_time_1, col_time_2, col_item = st.columns([1, 1, 1])
    
    # Year Selection (複数選択)
    available_years = sorted(df_market_potential_base['year'].unique().tolist(), reverse=True)
    latest_year = available_years[0] if available_years else None
    
    if 'potential_selected_years_state' not in st.session_state:
        st.session_state.potential_selected_years_state = [latest_year] if latest_year else []
    
    valid_years = [y for y in st.session_state.potential_selected_years_state if y in available_years]
    if not valid_years:
        valid_years = [latest_year] if latest_year else []
    st.session_state.potential_selected_years_state = valid_years

    with col_time_1:
        selected_years = st.multiselect(
            "分析対象年を選択 (複数選択可)",
            available_years, 
            default=st.session_state.potential_selected_years_state, 
            key='potential_selected_years_key'
        )
        st.session_state.potential_selected_years_state = selected_years 

    if not selected_years:
        st.warning("分析対象年を少なくとも1つ選択してください。")
        st.stop()
        
    df_filtered_years = df_market_potential_base[df_market_potential_base['year'].isin(selected_years)]
    
    # Quarter Selection (Only for Quarterly Analysis) - 複数選択
    selected_quarters = [''] 
    
    if analysis_level == "四半期別":
        available_quarters = sorted(df_filtered_years['Quarter'].unique().tolist())
        
        if 'potential_selected_quarters_state' not in st.session_state:
            st.session_state.potential_selected_quarters_state = available_quarters
            
        valid_quarters = [q for q in st.session_state.potential_selected_quarters_state if q in available_quarters]
        if not valid_quarters:
            valid_quarters = available_quarters
        st.session_state.potential_selected_quarters_state = valid_quarters
        
        with col_time_2:
            # バブルチャートの対象四半期はここで選択する
            selected_quarters = st.multiselect(
                "バブルチャートの四半期を選択 (複数選択可)",
                available_quarters, 
                default=st.session_state.potential_selected_quarters_state, 
                key='potential_selected_quarters_key'
            )
            st.session_state.potential_selected_quarters_state = selected_quarters 
        
        if not selected_quarters:
            st.warning("分析対象の四半期を少なくとも1つ選択してください。")
            st.stop()
            
        df_for_country_selection = df_filtered_years[df_filtered_years['Quarter'].isin(selected_quarters)].copy()
        
    else:
        df_for_country_selection = df_filtered_years.copy()
        col_time_2.empty() 

    # Item Selection
    current_potential_items = POTENTIAL_ITEMS_DICT.get(item_category, ['全体'])
    
    if 'potential_selected_item_state' not in st.session_state:
        st.session_state.potential_selected_item_state = '全体'
        
    if st.session_state.potential_selected_item_state not in current_potential_items:
        st.session_state.potential_selected_item_state = '全体'

    try:
        default_index = current_potential_items.index(st.session_state.potential_selected_item_state)
    except ValueError:
        default_index = current_potential_items.index('全体') if '全体' in current_potential_items else 0
    
    with col_item:
        selected_item = st.selectbox(
            f"Y軸の消費単価項目を選択 ({item_category})",
            current_potential_items,
            index=default_index,
            key='potential_selected_item_key'
        )
    
    st.session_state.potential_selected_item_state = selected_item

    # Country Selection
    all_countries_sorted = get_country_list_sorted(df_for_country_selection, country_col_name='country')
    all_countries = [c for c in all_countries_sorted if c != '全国籍･地域']

    default_countries_initial = get_safe_default_countries(all_countries, max_list_count=8)

    if 'potential_selected_countries_state' not in st.session_state:
        st.session_state.potential_selected_countries_state = [c for c in default_countries_initial if c in all_countries]

    valid_countries = [c for c in st.session_state.potential_selected_countries_state if c in all_countries]
    if not valid_countries:
        valid_countries = [c for c in default_countries_initial if c in all_countries]
    st.session_state.potential_selected_countries_state = valid_countries
    
    selected_countries = st.multiselect(
        "分析対象国・地域を選択 (複数選択可)",
        all_countries,
        default=st.session_state.potential_selected_countries_state, 
        key='potential_selected_countries_key'
    )
    st.session_state.potential_selected_countries_state = selected_countries 
    
    if not selected_countries:
        st.warning("分析対象国・地域を少なくとも1つ選択してください。")
        st.stop()
        
    # グラフ描画のためのデータ準備とループ
    
    if selected_item == '全体':
        spend_col = 'Avg_Total_Spend'
        spend_label = '消費単価 (円)'
    else:
        spend_col = selected_item
        spend_label = f'{selected_item}の消費単価 (円)'

    list_of_dataframes = []
    
    # 時系列プロットのためのデータ (選択された全ての国・費目、全期間)
    # df_time_series_base_allは年次または四半期すべての期間のデータを持つ
    df_time_series_base = df_time_series_base_all.copy()
    
    if analysis_level == "年次 (年間総計)":
        # バブルチャート用に選択された年のみのデータリストを構築
        for y in selected_years:
            df_plot_y = df_market_potential_base[df_market_potential_base['year'] == y].copy()
            if not df_plot_y.empty:
                list_of_dataframes.append((f"{y}年", df_plot_y))
        
    else: # 四半期別
        # バブルチャート用に選択された年と四半期の組み合わせのデータリストを構築 (ユーザー選択に限定)
        combinations = list(product(selected_years, selected_quarters))
        
        for y, q in combinations:
            df_plot_yq = df_market_potential_base[
                (df_market_potential_base['year'] == y) & 
                (df_market_potential_base['Quarter'] == q)
            ].copy()
            
            if not df_plot_yq.empty:
                list_of_dataframes.append((f"{y}年 {q}", df_plot_yq))
    
    if not list_of_dataframes and df_time_series_base.empty:
        st.warning(f"選択された期間、費目、および国・地域で有効なデータが見つかりませんでした。データが連続していない可能性があります。")
        return

    # 時系列データセットのフィルタリングと計算
    df_time_series_base = df_time_series_base[df_time_series_base['country'].isin(selected_countries)].copy()
    
    if spend_col not in df_time_series_base.columns or df_time_series_base[spend_col].isnull().all():
        st.warning(f"選択された項目（{selected_item}）の消費単価データが不足しているため、ポテンシャル計算およびグラフ描画ができません。")
        return
        
    df_time_series_base['Current_Market_Potential'] = df_time_series_base[visitors_col] * df_time_series_base[spend_col]
    
    # NaN値のみを除外する（市場ポテンシャルが0のデータは残す）
    df_time_series_final = df_time_series_base.dropna(subset=['Current_Market_Potential']).copy()

    if df_time_series_final.empty:
        st.info(f"選択された国・地域または項目（{selected_item}）で有効な時系列データが見つかりませんでした。（ポテンシャル計算結果が全てデータ不足でした）")

    # 注釈テキストの定義
    SOURCE_CAPTION = "出典：日本政府観光局（JNTO）/観光庁より作成"
    
    # 詳細な計算注釈 (画面下部に一度だけ表示する)
    DETAIL_NOTES_HTML = f"""
        <p style='font-size: small; color: #888888;'>
            ※訪日客数はJNTOの月次データを基にした{analysis_level}の合計値、消費単価は観光庁の四半期データを基にした{analysis_level}の平均値を使用しています。<br>
            ※ポテンシャル値は「訪日客数 × 選択された項目（{item_category}）の消費単価」として計算しています。 
        </p> 
        """
    
    # ============================================
    # グラフ描画
    # ============================================

    # バブルチャートの描画
    is_bubble_chart_displayed = False
    for time_title, df_plot in list_of_dataframes:

        # ============================================================
        # 中央値算出（固定基準）：全対象国（母集団）で作る
        # ※選択国で絞る前に、log可能・必要列ありのデータを作る
        # ============================================================
        df_base_all = df_plot.copy()

        # 除外（全国籍・地域など集計行がある場合）
        df_base_all = df_base_all[df_base_all['country'] != '全国籍･地域'].copy()

        # 消費単価列チェック（母集団に列が無い/欠損だらけならスキップ）
        if spend_col not in df_base_all.columns or df_base_all[spend_col].isnull().all():
            st.info(f"{time_title} のデータは、選択された項目（{selected_item}）の消費単価データが不足しているため、スキップされます。")
            continue

        # 市場ポテンシャル（元スケール）
        df_base_all['Current_Market_Potential'] = df_base_all[visitors_col] * df_base_all[spend_col]

        # NaN除外（中央値計算・散布図の両方で必要）
        df_base_all = df_base_all.dropna(subset=['Current_Market_Potential', visitors_col, spend_col]).copy()

        # 対数軸対応：0以下を除外（log不可）
        df_base_all = df_base_all[(df_base_all[visitors_col] > 0) & (df_base_all[spend_col] > 0)].copy()

        if df_base_all.empty:
            st.info(f"{time_title} のデータは、対数表示に必要な正の値データが不足しているため、スキップされます。")
            continue

        # 中央値（対数空間で計算）→ 元スケールへ戻す（固定基準線）
        median_log_visitors = np.log(df_base_all[visitors_col]).median()
        median_log_spend = np.log(df_base_all[spend_col]).median()
        median_visitors = float(np.exp(median_log_visitors))
        median_spend = float(np.exp(median_log_spend))

        # ============================================================
        # 表示・象限分類：選択国だけに絞る（基準線は上で固定）
        # ============================================================
        df_plot_final = df_base_all[df_base_all['country'].isin(selected_countries)].copy()

        if df_plot_final.empty:
            st.info(f"{time_title} のデータは、選択された国・地域が表示条件（対数表示可能な正の値）を満たさないため、スキップされます。")
            continue

        is_bubble_chart_displayed = True

        # バブルチャート本体（X/Yとも対数）
        fig_potential = px.scatter(
            df_plot_final,
            x=visitors_col,
            y=spend_col,
            size='Current_Market_Potential',
            color='country',
            hover_name='country',
            log_x=True,
            log_y=True,
            title=f"{time_title} {title_suffix} マーケットポテンシャル ({selected_item})",
            labels={
                visitors_col: visitors_label,            # 既に [対数] 前提
                spend_col: f"{spend_label} [対数]",       # 対数であることを明記
                'Current_Market_Potential': f'市場ポテンシャル (訪日客数 × {selected_item}の一人あたり消費額)'
            },
            height=650
        )

        # 4象限ライン（母集団の対数中央値を元スケールで描画＝固定）
        fig_potential.add_vline(
            x=median_visitors,
            line_dash="dash",
            line_color="red",
            annotation_text=f"訪日客数（全対象国・対数中央値）({median_visitors:,.0f})",
            annotation_position="top"
        )
        fig_potential.add_hline(
            y=median_spend,
            line_dash="dash",
            line_color="blue",
            annotation_text=f"消費単価（全対象国・対数中央値）(¥{median_spend:,.0f})"
        )

        # バブルサイズ調整
        max_potential = df_plot_final['Current_Market_Potential'].max()
        sizeref_value = 2 * max_potential / (70**2) if max_potential > 0 else 1
        fig_potential.update_traces(marker=dict(sizemode='area', sizeref=sizeref_value, sizemin=4))

        # 軸の見た目（任意：対数でも読みやすい表記に）
        log_ticks_visitors = [10_000, 100_000, 1_000_000, 10_000_000, 100_000_000]
        fig_potential.update_xaxes(
            tickformat=',.0f',
            tickmode='array',
            tickvals=log_ticks_visitors,
            automargin=True,
            ticklabelposition="outside bottom",
            ticks="outside"
        )

        fig_potential.update_yaxes(
            tickformat=',.0f',
            tickprefix='¥',
            automargin=True
        )

        fig_potential = fig_potential.update_layout(
            margin=dict(b=100),
            legend_title_text='国・地域',
            annotations=[
                dict(
                    text=SOURCE_CAPTION,
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=1,
                    y=-0.15,
                    xanchor='right',
                    yanchor='top',
                    font=dict(size=10, color="gray")
                )
            ]
        )

        st.plotly_chart(fig_potential, use_container_width=True)

        # ----------------------------------------------------------------------
        # 象限（HH/LH/HL/LL）を自動付与（固定中央値＝全対象国基準）
        # ----------------------------------------------------------------------
        def assign_quadrant(v, s, mv, ms):
            if (v >= mv) and (s >= ms):
                return "HH"
            elif (v < mv) and (s >= ms):
                return "LH"
            elif (v >= mv) and (s < ms):
                return "HL"
            else:
                return "LL"

        df_plot_final['Quadrant'] = df_plot_final.apply(
            lambda r: assign_quadrant(r[visitors_col], r[spend_col], median_visitors, median_spend),
            axis=1
        )

        quadrant_name_map = {
            "HH": "戦略的中核市場（量×質）",
            "LH": "高付加価値市場（質重視）",
            "HL": "量主導市場（単価改善余地）",
            "LL": "限定対応市場（探索・維持）"
        }
        df_plot_final['Quadrant_Name'] = df_plot_final['Quadrant'].map(quadrant_name_map)

        # ----------------------------------------------------------------------
        # 象限別サマリー（表示対象＝選択国）
        # ----------------------------------------------------------------------
        df_quadrant_summary = (
            df_plot_final
            .groupby(['Quadrant', 'Quadrant_Name'], as_index=False)
            .agg(
                Countries=('country', 'nunique'),
                Total_Visitors=(visitors_col, 'sum'),
                Avg_Spend=(spend_col, 'mean'),
                Total_Potential=('Current_Market_Potential', 'sum')
            )
        )

        order = pd.CategoricalDtype(categories=["HH", "LH", "HL", "LL"], ordered=True)
        df_quadrant_summary['Quadrant'] = df_quadrant_summary['Quadrant'].astype(order)
        df_quadrant_summary = df_quadrant_summary.sort_values('Quadrant')

        st.markdown(f"<h4 style='font-size: 1.25rem;'>{time_title}｜4象限サマリー</h4>", unsafe_allow_html=True)
        
        st.dataframe(
            df_quadrant_summary.style.format({
                "Total_Visitors": "{:,.0f}",
                "Avg_Spend": "¥{:,.0f}",
                "Total_Potential": "¥{:,.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------------------------
        # 象限別：国リスト
        # ----------------------------------------------------------------------
        TOP_N = 20
        st.markdown(f"<h4 style='font-size: 1.25rem;'>{time_title}｜象限別 国リスト</h4>", unsafe_allow_html=True)

        for q in ["HH", "LH", "HL", "LL"]:
            df_q = df_plot_final[df_plot_final["Quadrant"] == q].copy()
            if df_q.empty:
                st.markdown(f"<h5 style='font-size: 1.1rem;'>{q}：該当なし</h5>", unsafe_allow_html=True)
                continue

            df_q = df_q.sort_values("Current_Market_Potential", ascending=False)

            st.markdown(f"<h5 style='font-size: 1.1rem;'>{q}：{quadrant_name_map[q]}</h5>", unsafe_allow_html=True)

            show_cols = ["country", visitors_col, spend_col, "Current_Market_Potential"]
            df_show = df_q[show_cols].head(TOP_N).rename(columns={
                visitors_col: "Annual_Visitors",
                spend_col: "Avg_Spend",
                "Current_Market_Potential": "Market_Potential"
            })

            st.dataframe(
                df_show.style.format({
                    "Annual_Visitors": "{:,.0f}",
                    "Avg_Spend": "¥{:,.0f}",
                    "Market_Potential": "¥{:,.0f}",
                }),
                use_container_width=True,
                hide_index=True
            )

    # バブルチャートが表示されたら区切り線を入れる
    if is_bubble_chart_displayed:
        st.markdown("---")


    # 時系列推移グラフの描画 (時系列推移データがある場合のみ)
    if not df_time_series_final.empty:
        
        # 四半期分析の場合は、Time_Indexを正しい順序でソートする
        if analysis_level == "四半期別":
            quarters_order = ['Q1', 'Q2', 'Q3', 'Q4']
            
            # データ内の全ての年と四半期を取得し、適切な順序で Time_Index を作成
            all_years = sorted(df_time_series_final['year'].unique())
            all_time_indices = []
            for y in all_years:
                for q in quarters_order:
                    index = f"{y}-{q}"
                    # 存在するインデックスのみをリストに追加
                    if index in df_time_series_final['Time_Index'].unique():
                        all_time_indices.append(index)

            # Time_Indexをソートキーとする一時的な辞書を作成し、ソート
            sort_mapping = {index: i for i, index in enumerate(all_time_indices)}
            df_time_series_final['Time_Index_Sort'] = df_time_series_final['Time_Index'].map(sort_mapping)
            df_time_series_final = df_time_series_final.sort_values(by=['country', 'Time_Index_Sort']).drop(columns=['Time_Index_Sort'])
            
        # 注意：この後のプロットではTime_Indexは文字列として使用し、Categoricalにはしない
        # 年次データの場合は、Time_Index (文字列) が既にソート済みであることを前提とする
        
        fig_trend = px.line(
            df_time_series_final,
            x='Time_Index', # X軸は文字列のまま使用
            y='Current_Market_Potential', 
            color='country', 
            markers=True, 
            title=f"市場ポテンシャル ({selected_item}) の時系列推移 ({title_suffix})",
            labels={
                'Time_Index': '期間',
                'Current_Market_Potential': f'市場ポテンシャル (訪日客数 × {selected_item}単価) [円]'
            },
            height=600
        )

        fig_trend.update_yaxes(tickformat='~s') # 軸の単位を簡略化 (例: 10M, 10G)
        
        fig_trend.update_xaxes(
            tickangle=-45,
            automargin=True,
            showticklabels=True, # ラベル表示を強制（重なり過ぎたらPlotlyが自動で省略するが、まずは表示を試みる）
        )

        fig_trend = fig_trend.update_layout(
            margin=dict(b=100), # 下部マージンの調整
            legend_title_text='国・地域',
            annotations=[ 
                dict(
                    text=SOURCE_CAPTION,
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=1, 
                    y=-0.15, 
                    xanchor='right',
                    yanchor='top',
                    font=dict(size=10, color="gray")
                )
            ]
        )

        st.plotly_chart(fig_trend, use_container_width=True)

    # ============================================
    # 画面下部の注釈
    # ============================================
    st.markdown("---")
    st.markdown(DETAIL_NOTES_HTML, unsafe_allow_html=True)
    # ============================================

# ページ関数を実行
if 'df_market_potential_yearly' in st.session_state:
    page_market_potential_analysis()