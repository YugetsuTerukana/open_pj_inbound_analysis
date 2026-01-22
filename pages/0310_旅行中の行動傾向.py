import streamlit as st
import pandas as pd
import plotly.express as px

if 'df_pca_scores' not in st.session_state:
    st.error("必要なデータがロードされていません。Homeに戻ってデータロードを確認してください。")
    st.stop()

# データをセッションステートから取得
df_pca_scores = st.session_state.df_pca_scores
# PCラベル関数もセッションステートから取得
get_pc_label = st.session_state.get_pc_label


def page_travel_action_trend():
    
    st.header("国・地域別 行動傾向分布 (PCAスコア)")
    st.markdown("""
        主成分分析（PCA）により抽出された主成分軸（PC）に基づく国・地域別の行動傾向の分布を示します。
        
        * **PC1 (関心深度):** **日本文化への関心・体験** (スコアが高いほど日本文化への関心・体験が高い)
        * **PC2 (スタイル):** **アクティブ志向 vs 和の寛ぎ・食志向** (正: テーマパーク/四季の体感/ショッピング、負: 温泉/旅館/日本食)
        * **PC3 (ジャンル):** **自然・地方志向 vs 都市型娯楽志向** (正: 四季の体感・スキー/ゴルフ、負: ポップカルチャー/映画・アニメ)
    """)
    
    if df_pca_scores.empty or 'Year' not in df_pca_scores.columns or 'country' not in df_pca_scores.columns:
        st.warning("PCスコアデータが見つかりません。`pca_scores_timeseries.csv`を確認してください。")
        st.stop()
        
    available_years = sorted(df_pca_scores['Year'].unique().tolist(), reverse=True)
    latest_year = available_years[0] if available_years else None
    
    pc_options_all = [col for col in df_pca_scores.columns if col.startswith('PC')]
    
    if not pc_options_all:
        st.warning("PCA軸データが見つかりません。")
        st.stop()

    # 状態保持のための初期化ロジック
    if 'pca_selected_year' not in st.session_state:
        st.session_state.pca_selected_year = latest_year
    if 'pca_x_axis' not in st.session_state:
        st.session_state.pca_x_axis = 'PC2' if 'PC2' in pc_options_all else (pc_options_all[0] if pc_options_all else None)
    if 'pca_y_axis' not in st.session_state:
        st.session_state.pca_y_axis = 'PC3' if 'PC3' in pc_options_all else (pc_options_all[1] if len(pc_options_all) > 1 else (pc_options_all[0] if pc_options_all else None))
    if 'pca_color_axis' not in st.session_state:
        st.session_state.pca_color_axis = 'PC1' if 'PC1' in pc_options_all else 'なし'
        
    # 年の選択

    # 選択肢 available_years に現在の選択値が存在しない場合、初期値のlatest_yearに戻す
    if st.session_state.pca_selected_year not in available_years:
        st.session_state.pca_selected_year = latest_year
    
    # Streamlitエラー回避のためのインデックス計算
    try:
        # セッションステートの値が選択肢にある場合のインデックスを計算
        year_initial_index = available_years.index(st.session_state.pca_selected_year)
    except ValueError:
        # 見つからない場合は最新年または0番目
        year_initial_index = available_years.index(latest_year) if latest_year in available_years else 0

    selected_year = st.selectbox(
        "分析対象年を選択", 
        available_years, 
        # 計算済みのインデックスを渡す
        index=year_initial_index, 
        key='pca_selected_year_key'
    )
    # ウィジェットの値を次の実行のためにセッションステートに保存
    st.session_state.pca_selected_year = selected_year
    
    st.markdown("---")
    
    # 選択された年のデータにフィルタリング
    df_plot_pca = df_pca_scores[df_pca_scores['Year'] == selected_year].copy()
    
    # 軸の選択 (現在のYearで利用可能なPCオプションを再定義)
    pc_options = [col for col in df_plot_pca.columns if col.startswith('PC')]
    color_axis_options = pc_options + ['なし']

    if not pc_options:
        st.warning("PC軸データが見つかりません。")
        st.stop()

    # 選択肢の整合性チェック: 以前の選択値が現在の選択肢リストに存在するか確認し、なければデフォルト値にリセット
    if st.session_state.pca_x_axis not in pc_options:
        st.session_state.pca_x_axis = 'PC2' if 'PC2' in pc_options else (pc_options[0] if pc_options else None)
    if st.session_state.pca_y_axis not in pc_options:
        st.session_state.pca_y_axis = 'PC3' if 'PC3' in pc_options else (pc_options[1] if len(pc_options) > 1 else (pc_options[0] if pc_options else None))
    if st.session_state.pca_color_axis not in color_axis_options:
        st.session_state.pca_color_axis = 'PC1' if 'PC1' in pc_options else 'なし'

    # インデックス計算
    x_index = pc_options.index(st.session_state.pca_x_axis) if st.session_state.pca_x_axis in pc_options else 0
    # Y軸のインデックスは、X軸と重複しないように調整される可能性があるため、デフォルト値のみ計算
    y_index = pc_options.index(st.session_state.pca_y_axis) if st.session_state.pca_y_axis in pc_options else 1
    color_index = color_axis_options.index(st.session_state.pca_color_axis) if st.session_state.pca_color_axis in color_axis_options else (len(color_axis_options) - 1 if color_axis_options else 0)

    st.subheader(f"{selected_year}年: 行動傾向散布図")
    st.markdown("X軸、Y軸、色軸のPCスコアを選択して、国・地域間の行動傾向の分布を分析できます。")
    st.markdown("---")
    col_x, col_y, col_color = st.columns(3)
    
    with col_x:
        x_axis = st.selectbox(
            "X軸 (主軸) の選択", 
            pc_options, 
            index=x_index,
            format_func=get_pc_label,
            key='pca_x_axis_key' 
        )
    with col_y:
        y_axis = st.selectbox(
            "Y軸 (副軸) の選択", 
            pc_options, 
            index=y_index,
            format_func=get_pc_label,
            key='pca_y_axis_key' 
        )
    with col_color:
        color_axis = st.selectbox(
            "色軸 (第3の軸) の選択", 
            color_axis_options, 
            index=color_index,
            format_func=get_pc_label,
            key='pca_color_axis_key' 
        )

    # ウィジェットの値を、次回実行時のデフォルト値としてセッションステートに保存
    st.session_state.pca_x_axis = x_axis
    st.session_state.pca_y_axis = y_axis
    st.session_state.pca_color_axis = color_axis

    if x_axis == y_axis:
        st.error("X軸とY軸には異なる主成分を選択してください。")
        st.stop()

    # 散布図の作成
    
    x_label = get_pc_label(x_axis) + "スコア"
    y_label = get_pc_label(y_axis) + "スコア"
    
    # 色軸の設定
    if color_axis != 'なし':
        df_plot_pca['color_value'] = df_plot_pca[color_axis]
        color_name = get_pc_label(color_axis)
        
        color_scale = 'RdBu' 
        color_midpoint = 0 
        
        fig_pca = px.scatter(
            df_plot_pca, 
            x=x_axis, 
            y=y_axis, 
            color='color_value',
            hover_name='country',
            title=f"{selected_year}年: 国・地域別 行動傾向分布 ({x_axis} vs {y_axis})",
            labels={x_axis: x_label, y_axis: y_label, 'color_value': color_name + 'スコア'},
            color_continuous_scale=color_scale,
            color_continuous_midpoint=color_midpoint,
            text='country',
            height=600
        )
        # カラーバーのタイトルを修正
        fig_pca.update_layout(coloraxis_colorbar=dict(title=color_name))
    else:
        fig_pca = px.scatter(
            df_plot_pca, 
            x=x_axis, 
            y=y_axis, 
            hover_name='country',
            title=f"{selected_year}年: 国・地域別 行動傾向分布 ({x_axis} vs {y_axis})",
            labels={x_axis: x_label, y_axis: y_label},
            text='country',
            height=600,
            color='country' # 色軸なしの場合は国別で色分け
        )

    # テキストラベルの設定とマーカーサイズ調整
    fig_pca.update_traces(textposition='top center', mode='markers+text', marker=dict(size=10, opacity=0.8))
    
    # X軸とY軸の比率を1:1に保つ (分布の形状を歪ませないため)
    fig_pca.update_layout(
        autosize=True,
        xaxis=dict(scaleanchor="y", scaleratio=1), 
        yaxis=dict(scaleratio=1),
    )
    
    # 原点に十字線
    fig_pca.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", annotation_text="平均 (0)", annotation_position="top left")
    fig_pca.add_vline(x=0, line_width=1, line_dash="dash", line_color="gray", annotation_text="平均 (0)", annotation_position="bottom right")

    # 出典注釈
    fig_pca = fig_pca.update_layout(
        annotations=[
            dict(
                text="出典：日本政府観光局（JNTO）より作成",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=1, 
                y=-0.11, 
                font=dict(size=10, color="gray"),
                align="right"
            )
        ],
        margin=dict(b=50) 
    )
    
    st.plotly_chart(fig_pca, use_container_width=True) 
    
    st.markdown("""
        <p style='font-size: small; color: #888888;'>
        ※このグラフは、選択された2つの主成分（PC）軸を元に、各国・地域がその行動傾向をどの程度持っているか（PCスコア）をプロットしたものです。<br>
        ※PCスコアが0に近いほど、全国籍・地域の平均的な行動傾向に近いことを示します。<br>
        ※X軸とY軸の比率が1:1になるように調整しています。
        </p>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("---")

    # レーダーチャート (全PC軸の比較)
    st.subheader(f"{selected_year}年: レーダーチャートによる行動傾向の比較")

    all_countries_year = df_plot_pca['country'].unique().tolist()
    
    # 複数選択の初期値設定
    if 'pca_countries_multiselect' not in st.session_state:
        # 散布図の表示前に初期値を設定
        from app.utils import get_safe_default_countries
        initial_default_countries = get_safe_default_countries(all_countries_year, max_list_count=4)
        st.session_state.pca_countries_multiselect = initial_default_countries
        
    current_selection = st.session_state.pca_countries_multiselect
    valid_selection = [c for c in current_selection if c in all_countries_year]
    st.session_state.pca_countries_multiselect = valid_selection
    
    selected_countries_radar = st.multiselect(
        "比較する国を選択 (レーダーチャート)", 
        all_countries_year,
        default=["中国","米国"],
        key='pca_countries_multiselect_key'
    )
    st.session_state.pca_countries_multiselect = selected_countries_radar

    if not selected_countries_radar:
        st.info("比較したい国を1つ以上選択してください。")
        st.stop()
        
    if len(pc_options) < 3:
        st.warning("レーダーチャートを表示するには、少なくとも3つのPC軸が必要です。")
        st.stop()

    df_radar_base = df_plot_pca[df_plot_pca['country'].isin(selected_countries_radar)].copy()
    
    # Meltしてレーダーチャート用に整形
    df_radar_melted = df_radar_base.melt(
        id_vars=['country'],
        value_vars=pc_options,
        var_name='PC軸',
        value_name='PCスコア'
    )
    
    # PC軸に解釈ラベルを付与
    df_radar_melted['PC軸_ラベル'] = df_radar_melted['PC軸'].apply(get_pc_label)
    
    # PCスコアの絶対値の最大値を計算し、レーダーチャートの軸の最大値を決定
    max_radar_score = df_pca_scores[pc_options_all].abs().max().max() * 1.1
    
    fig_radar = px.line_polar(
        df_radar_melted,
        r='PCスコア',
        theta='PC軸_ラベル',
        color='country',
        line_close=True,
        title=f'{selected_year}年 各国・地域の行動傾向レーダーチャート',
        height=600
    )
    
    # 軸の最大値と中心線 (0) の設定
    fig_radar.update_traces(fill='toself')
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[-max_radar_score, max_radar_score], # 軸の範囲を固定
                showline=False,
                tickvals=[-max_radar_score/2, 0, max_radar_score/2, max_radar_score],
                ticktext=[f'{-max_radar_score/2:.1f}', '0 (平均)', f'{max_radar_score/2:.1f}', f'{max_radar_score:.1f}'],
                showticklabels=True
            ),
        ),
        legend_title="国・地域",
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)
    
    # 画面下部の注釈
    st.markdown(
        """
        <p style='font-size: small; color: #888888;'>
        ※PCスコアが0から大きく離れるほど、その行動傾向が全体平均からかけ離れていることを意味します。<br>
        ※各PC軸の解釈については、本ページ上部またはデータロード時の説明を参照してください。
        </p>
        """,
        unsafe_allow_html=True
    )
    
page_travel_action_trend()