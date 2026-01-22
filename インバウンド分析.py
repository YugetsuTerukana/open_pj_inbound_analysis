import streamlit as st

st.set_page_config(
    page_title="インバウンド分析ダッシュボード",
    page_icon="🇯🇵",
    layout="wide",
)


# 💡 修正: アプリ起動時、メニューの Home.py に自動的に切り替える
# ページ名は、pages/ ディレクトリからの相対パス（拡張子なし）が基本ですが、
# Streamlitのバージョンによってはファイル名全体（pages/Home.py）で指定する必要があります。
try:
    # ページファイルのパスを指定してリダイレクト
    st.switch_page("pages/0001_Home.py") 
except Exception:
    # 古いバージョンなど、pages/ を省略できる場合の代替
    try:
        st.switch_page("0001_Home.py") 
    except Exception:
        # どうしてもリダイレクトできない場合は、以前の案内を表示
        st.title("インバウンド分析ダッシュボード")
        st.info("アプリのメインコンテンツは、左側のメニューから各分析ページを選択してご覧ください。")