import streamlit as st
import pandas as pd
import numpy as np 
import os
from datetime import timedelta
from itertools import product 

# ============================================
# データ読込関数
# ============================================
@st.cache_data
def load_data():
    """
    必要なデータファイルを読み込み、分析しやすい形式に前処理する関数。
    費目別および細目別の消費単価をポテンシャル分析データに追加します。
    """
    
    df_destination = pd.DataFrame()
    df_pca_scores = pd.DataFrame()

    try:
        # 必須ファイル ---
        file_jnto = "data/inbound_visiter.csv"
        file_spend = "data/inbound_spending.csv"

        df_jnto = pd.read_csv(file_jnto)
        df_spend = pd.read_csv(file_spend)
        
        # その他のファイル ---
        try:
            df_destination = pd.read_csv("data/inbound_destination.csv")
        except FileNotFoundError:
            df_destination = pd.DataFrame() 
        
        try:
            df_pca_scores = pd.read_csv("data/pca_scores_timeseries.csv")
        except FileNotFoundError:
            df_pca_scores = pd.DataFrame() 
            
    except FileNotFoundError as e:
        st.error(f"必須ファイルが見つかりません: {e.filename}。ファイル名またはパスを確認してください。")
        st.stop()
        return None, None, None, None, None, None, None, None, None
    
    # --- df_jnto (訪日客数) 前処理 ---
    df_jnto["date"] = pd.to_datetime(df_jnto["Year"].astype(str) + "-" + df_jnto["Month_Numeric"].astype(str))
    df_jnto_pivot = df_jnto.pivot_table(index="date", columns="Country/Area", values="Visitor_Numeric")
    
    df_jnto_yearly = df_jnto.groupby(['Year', 'Country/Area'])['Visitor_Numeric'].sum().reset_index()
    df_jnto_yearly.rename(columns={'Visitor_Numeric': 'Annual_Visitors', 'Country/Area': 'country', 'Year': 'year'}, inplace=True)
    
    df_jnto['Quarter_Numeric'] = df_jnto['Month_Numeric'].apply(lambda m: (m - 1) // 3 + 1)
    df_jnto['Quarter'] = df_jnto['Quarter_Numeric'].astype(str) + 'Q'
    
    df_jnto_quarterly = df_jnto.groupby(['Year', 'Quarter', 'Country/Area'])['Visitor_Numeric'].sum().reset_index()
    df_jnto_quarterly.rename(columns={'Visitor_Numeric': 'Quarterly_Visitors', 'Country/Area': 'country', 'Year': 'year'}, inplace=True)
    
    
    # --- df_spend (消費額) 前処理 ---
    pattern_to_exclude = '全体|TOTAL|ALL'
    
    df_spend_items_all = df_spend[
        (~df_spend['expense_items'].str.contains(pattern_to_exclude, case=False, na=False, regex=True))
    ].copy()
    
    df_spend_items_all['item_name'] = df_spend_items_all.apply(
        lambda row: f"{row['expense_items']} [{row['details']}]" if row['details'] != 'all' 
            else f"{row['expense_items']} [全体]",
        axis=1
    )
    
    all_consumption_items_ordered = df_spend_items_all['item_name'].drop_duplicates().tolist()
    
    df_spend_items_major = df_spend_items_all[df_spend_items_all['details'] == 'all'].copy()

    
    df_total_all = df_spend[
        (df_spend['expense_items'].str.contains(pattern_to_exclude, case=False, na=False, regex=True)) & 
        (df_spend['details'] == 'all')
    ]
    df_total_all = df_total_all.groupby(['year', 'country', 'Quarter'])['consumption_unit'].mean().reset_index()
    df_total_all.rename(columns={'consumption_unit': 'Avg_Total_Spend'}, inplace=True)

    df_unit_pivot_all = df_spend_items_all.pivot_table(
        index=['year', 'country', 'Quarter'], 
        columns='item_name', 
        values='consumption_unit'
    ).fillna(0)

    df_unit_pivot_all.reset_index(inplace=True)


    # 四半期ポテンシャル分析用データフレームの構築
    df_avg_spend_quarterly = df_total_all.merge(
        df_unit_pivot_all, 
        on=['year', 'country', 'Quarter'],
        how='left'
    ).fillna(0)
    
    # 年次ポテンシャル分析用データフレームの構築
    df_avg_spend_yearly_temp = df_avg_spend_quarterly.drop(columns=['Quarter'], errors='ignore')
    df_avg_spend_yearly_data = df_avg_spend_yearly_temp.groupby(['year', 'country']).mean().reset_index()
    
    df_avg_spend_yearly_old = df_avg_spend_yearly_data[['year', 'country', 'Avg_Total_Spend']].copy()
    df_avg_spend_yearly_old.rename(columns={'Avg_Total_Spend': 'Avg_Spend_Per_Visitor'}, inplace=True)

    # 結合とポテンシャル計算 (四半期)
    df_market_potential_quarterly = df_jnto_quarterly.merge(
        df_avg_spend_quarterly, 
        on=['year', 'country', 'Quarter'],
        how='inner'
    ).dropna(subset=['Quarterly_Visitors', 'Avg_Total_Spend'])

    df_market_potential_quarterly['Market_Potential_Total'] = df_market_potential_quarterly['Quarterly_Visitors'] * df_market_potential_quarterly['Avg_Total_Spend']

    # 結合とポテンシャル計算 (年次)
    df_market_potential_yearly = df_jnto_yearly.merge(
        df_avg_spend_yearly_data,
        on=['year', 'country'],
        how='inner'
    ).dropna(subset=['Annual_Visitors', 'Avg_Total_Spend'])

    df_market_potential_yearly['Market_Potential_Total'] = df_market_potential_yearly['Annual_Visitors'] * df_market_potential_yearly['Avg_Total_Spend']

    # df_avg_spend (費目割合/推移分析用)
    df_ratio_pivot = df_spend_items_major.pivot_table(index=['year', 'country', 'Quarter'], columns='expense_items', values='composition_ratio').fillna(0)
    df_unit_pivot_original = df_spend_items_major.pivot_table(index=['year', 'country', 'Quarter'], columns='expense_items', values='consumption_unit').fillna(0)
    df_ratio_pivot = df_ratio_pivot.add_suffix('_ratio')
    df_unit_pivot_original = df_unit_pivot_original.add_suffix('_unit')
    df_merged = df_ratio_pivot.merge(df_unit_pivot_original, on=['year', 'country', 'Quarter'], how='outer').fillna(0).reset_index()
    
    df_avg_spend = df_merged.merge(df_total_all.rename(columns={'Avg_Total_Spend': 'avg_total_spend_official'}), on=['year', 'country', 'Quarter'], how='left').set_index(['year', 'country', 'Quarter'])

    # df_destination/df_pca_scores
    if not df_destination.empty:
        df_destination_pivot = df_destination.pivot_table(index='Year', columns='Prefecture', values='Visit Rate(%)')
    else:
        df_destination_pivot = pd.DataFrame()

    if not df_pca_scores.empty:
        df_pca_scores.rename(columns={'Country/Area': 'country'}, inplace=True)
    
    return df_jnto_pivot, df_avg_spend, df_destination_pivot, df_pca_scores, df_jnto_yearly, df_avg_spend_yearly_old, df_market_potential_quarterly, df_market_potential_yearly, all_consumption_items_ordered


# ============================================
# 定数
# ============================================

# 費目ごとの固定色を定義（複数のメニューで使用）
COLOR_MAP = {
    '宿泊費': '#1f77b4', 
    '飲食費': '#ff7f0e', 
    '買物代': '#2ca02c', 
    '交通費': '#d62728', 
    '娯楽等サービス費': '#9467bd',
    'その他': '#8c564b', 
}
# 費目の固定順序を定義
ITEM_ORDER = ['買物代', '宿泊費', '飲食費', '娯楽等サービス費', '交通費', 'その他']

# PCA軸の解釈
PC_LABELS = {
    'PC1': 'PC1: 日本文化への関心と体験意欲',
    'PC2': 'PC2: アクティブ志向 vs 和の寛ぎ・食志向',
    'PC3': 'PC3: 自然・地方志向 vs 都市型娯楽志向',
}

# ============================================
# ヘルパー関数
# ============================================

def get_safe_default_countries(countries_in_year, max_list_count):
    if not countries_in_year:
        return []

    priority_countries_core = [
        "全国籍･地域", "韓国", "中国", "香港", "台湾", 
        "シンガポール", "米国", "オーストラリア", "フランス"
    ]
    
    default_countries = [c for c in priority_countries_core if c in countries_in_year]
    
    if "その他" in countries_in_year and "その他" not in default_countries and len(default_countries) < 9:
        default_countries.append("その他")

    return default_countries[:max_list_count]

def get_country_list_sorted_for_inbound(countries_list):
    countries_sorted = []
    if "全国籍･地域" in countries_list:
        countries_sorted.append("全国籍･地域")
    
    middle_countries = sorted([c for c in countries_list if c not in ["全国籍･地域", "その他"]])
    countries_sorted.extend(middle_countries)
    
    if "その他" in countries_list:
        countries_sorted.append("その他")
        
    return countries_sorted

def get_country_list_sorted(df_data, country_col_name='country'):
    if isinstance(df_data.index, pd.MultiIndex) and country_col_name in df_data.index.names:
        countries_in_data = list(set(df_data.index.get_level_values(country_col_name).tolist()))
    elif country_col_name in df_data.columns:
        countries_in_data = list(set(df_data[country_col_name].tolist()))
    else:
        if 'country' in df_data.columns:
            countries_in_data = list(set(df_data['country'].tolist()))
        else:
            return []
    
    countries_sorted = []
    if "全国籍･地域" in countries_in_data:
        countries_sorted.append("全国籍･地域")
    
    middle_countries = sorted([c for c in countries_in_data if c not in ["全国籍･地域", "その他"]])
    countries_sorted.extend(middle_countries)
    
    if "その他" in countries_in_data:
        countries_sorted.append("その他")
        
    return countries_sorted

def get_pc_label(pc_name):
    return PC_LABELS.get(pc_name, pc_name)

def format_delta_percent(rate):
    if np.isnan(rate):
        return "データなし"
    return f"{rate:+.1f} %"

def calculate_delta(target, comparison):
    if comparison is None or np.isnan(comparison):
        return np.nan, np.nan
    
    diff = target - comparison
    if comparison == 0:
        rate = 0.0 if diff == 0 else np.nan
    else:
        rate = (diff / comparison) * 100
        
    return diff, rate

def format_delta_abs(diff, prev_value):
    if prev_value is None or np.isnan(diff):
        return "データなし"

    if prev_value == 0 and diff == 0:
        return "0 人"
    if prev_value == 0 and diff != 0:
        return f"{diff:+,.0f} 人"
        
    return f"{diff:+,.0f} 人"