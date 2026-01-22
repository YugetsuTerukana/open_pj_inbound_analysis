import streamlit as st
import pandas as pd
import plotly.express as px
from app.utils import get_country_list_sorted, get_safe_default_countries

# データのロード確認とセッションステートからの取得
if 'df_avg_spend' not in st.session_state:
    st.error("必要なデータ (df_avg_spend) がロードされていません。Homeに戻ってデータロードを確認してください。")
    df_spend = pd.DataFrame() 
else:
    df_spend = st.session_state.df_avg_spend

def page_expense_unit_comparison():
    
    # データチェックと取得
    if 'df_market_potential_yearly' not in st.session_state:
        st.error("必要なデータがロードされていません。Homeに戻ってデータロードを確認してください。")
        # 関数を終了
        return 

    # 必要なデータをセッションステートから取得
    df_market_potential_yearly = st.session_state.df_market_potential_yearly

    ALL_CONSUMPTION_ITEMS_ORDERED = st.session_state.all_consumption_items_ordered
    SOURCE_CAPTION = st.session_state.SOURCE_CAPTION
    DEFAULT_YEAR = st.session_state.DEFAULT_YEAR

    # 費目/細目リストの再構築
    # '全体' と 'その他' を除く主要費目（[全体]を含むもの）をプルダウンの選択肢とする
    MAJOR_ITEMS_ORDERED = [
        item for item in ALL_CONSUMPTION_ITEMS_ORDERED 
        if '[全体]' in item 
        and item != '全体[全体]' 
        and not item.startswith('その他')
    ]

    # セレクトボックスに表示するためのリストを作成 (表示名から [全体] を削除)
    DISPLAY_MAJOR_ITEMS = [item.replace('[全体]', '') for item in MAJOR_ITEMS_ORDERED]

    # MAJOR_ITEMS_ORDERED（元のデータ名）と DISPLAY_MAJOR_ITEMS（表示名）を対応付けるための辞書を作成
    # 例: {'宿泊費': '宿泊費[全体]', '飲食費': '飲食費[全体]', ...}
    DISPLAY_TO_DATA_MAP = {display_name: data_name for display_name, data_name in zip(DISPLAY_MAJOR_ITEMS, MAJOR_ITEMS_ORDERED)}

    # =================================================================
    # Streamlit UI
    # =================================================================
    st.title("費目別消費単価比較")

    # フィルターとコントロール
    col1, col2 = st.columns([1, 1])

    with col1:
        # 費目の選択
        selected_display_item = st.selectbox(
            "比較する主要費目を選択してください",
            options=DISPLAY_MAJOR_ITEMS,
            index=0, # 最初の費目をデフォルトにする
            help="選択した費目について、その内訳（細目）を各国で比較します。"
        )
        # 選択された表示名から、データ処理に必要な元の費目名（例: 宿泊費[全体]）を取得
        selected_major_item = DISPLAY_TO_DATA_MAP.get(selected_display_item, selected_display_item + '[全体]')

    with col2:
        # 年度の選択 (データに存在する最新年度をデフォルトにする)
        available_years = sorted(df_market_potential_yearly['year'].unique().tolist(), reverse=True)
        selected_year = st.selectbox(
            "対象年度を選択してください",
            options=available_years,
            index=0
        )

    # データの前処理

    # 選択された主要費目の細目リストを取得
    major_item_root_name = selected_major_item.split('[')[0]
    if major_item_root_name == '全体':
        st.warning("「全体」を選択した場合、細目比較ができません。他の費目を選択してください。")
        return

    # 選択された主要費目に属する全ての細目の列名を抽出
    target_columns = [col for col in ALL_CONSUMPTION_ITEMS_ORDERED if col.startswith(major_item_root_name) and col != selected_major_item]

    # データのフィルタリングと集計
    
    # 選択された年度でフィルタリング
    df_filtered = df_market_potential_yearly[
        (df_market_potential_yearly['year'] == selected_year)
        & (df_market_potential_yearly['country'] != '全国籍･地域')
        & (df_market_potential_yearly['country'] != 'その他')
    ].copy()

    # 比較に必要な列を抽出: 'country', 選択された主要費目（合計値）、選択された細目
    columns_to_keep = ['country', selected_major_item] + target_columns
    df_chart_data = df_filtered[columns_to_keep].copy()

    # 主要費目の合計（積み上げ棒グラフの高さ）を計算し、降順ソートのキーにする
    df_chart_data['Total_Spend_for_Sort'] = df_chart_data[selected_major_item]

    # 降順でソート（棒グラフの高さが大きい国順に左から並べる）
    df_chart_data = df_chart_data.sort_values('Total_Spend_for_Sort', ascending=False)
    
    # 国・地域（X軸）の表示順をソートした順番に固定
    sorted_countries = df_chart_data['country'].tolist()


    # Plotlyのためのデータ整形 (細目の有無で分岐)
    
    # 細目データ (target_columns) が存在する場合 (通常の積み上げ棒グラフ)
    if len(target_columns) > 0:

        # 細目を列から行へ
        df_melted = df_chart_data.melt(
            id_vars=['country', 'Total_Spend_for_Sort'],
            value_vars=target_columns,
            var_name='細目',
            value_name='消費単価'
        )

        # 細目の名称を整形（例：'宿泊費_ホテル' -> 'ホテル'）
        df_melted['細目'] = df_melted['細目'].str.replace(major_item_root_name + '_', '')

        plot_data = df_melted
        color_param = '細目'
    
    # 細目データが存在しない場合 (主要費目全体の合計値を示す単一の棒グラフ)
    else:
        # 合計値データ (df_chart_data) をそのまま使用する形に整形
        df_single_bar = df_chart_data[['country', 'Total_Spend_for_Sort']].rename(
            columns={'Total_Spend_for_Sort': '消費単価'}
        )
        df_single_bar['細目'] = selected_major_item # 色分けのため、ダミーの細目を作成
        
        plot_data = df_single_bar
        color_param = None # 細目がないため色分けをしない

    # グラフの描画

    # グラフデータのチェックを plot_data に対して行う
    if plot_data.empty or df_chart_data['Total_Spend_for_Sort'].sum() == 0:
        st.warning(f"選択された条件 ({selected_year}年, 費目: {selected_display_item}) に該当するデータがありません。")
    else:
        # グラフの作成: 棒グラフ (colorパラメーターは上記で設定)
        fig_bar = px.bar(
            plot_data,
            x='country', 
            y='消費単価', 
            color=color_param, 
            title=f'{selected_display_item}の消費単価の国別比較 ({selected_year}年)',
            hover_data={
                '消費単価': ':.1f',  
                'country': True,
                '細目': True,
            },
            labels={
                'country': '国・地域',
                '消費単価': f'{major_item_root_name} 消費単価 (1人あたりの消費額)',
                '細目': '細目'
            },
            height=600
        )

        # X軸の表示順をソートした順番に固定
        fig_bar.update_xaxes(
            categoryorder='array',
            categoryarray=sorted_countries,
            tickangle=-45,
            automargin=True,
            showticklabels=True
        )

        # ツールチップのカスタマイズ (細目がある場合とない場合で挙動が変わるため、'Total_Spend_for_Sort'の表示は省略)
        if len(target_columns) > 0:
            # 積み上げグラフの場合、カスタムデータで合計額を表示
            fig_bar.update_traces(
                hovertemplate="<b>%{x}</b><br>細目: %{customdata[1]}<br>消費単価: %{y:.1f} 円/人<br>合計: %{customdata[0]:.1f} 円/人<extra></extra>", 
                customdata=df_melted[['Total_Spend_for_Sort', '細目']]
            )
        else:
            # 単一棒グラフの場合、合計額はY軸の値と同じ
            fig_bar.update_traces(
                hovertemplate="<b>%{x}</b><br>消費単価: %{y:.1f} 円/人<extra></extra>"
            )

        # レイアウトの調整と出典の表示
        fig_bar = fig_bar.update_layout(
            margin=dict(b=100), 
            legend_title_text='細目' if color_param else '',
            showlegend=bool(color_param), # 細目がなければ凡例を非表示
            annotations=[ 
                dict(
                    text=SOURCE_CAPTION,
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=1, 
                    y=-0.25, 
                    xanchor='right',
                    yanchor='top',
                    font=dict(size=10, color="gray")
                )
            ]
        )

        st.plotly_chart(fig_bar, use_container_width=True)

    # 注釈
    st.markdown(
        """
        <p style='font-size: small; color: #888888; margin-top: 20px;'>
        ※出典：観光庁「インバウンド消費動向調査」集計データ。<br>
        ※データは観光庁の調査の年/四半期平均値に基づいています。<br><br>
        </p>
        """,
        unsafe_allow_html=True
    )

# ページ関数を実行
if 'df_avg_spend' in st.session_state:
    page_expense_unit_comparison()