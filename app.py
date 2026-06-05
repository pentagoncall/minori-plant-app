import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import io
import base64
from datetime import datetime
import calendar

# --- 1. Firebaseの初期化 ---
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. アプリの基本設定 ---
st.set_page_config(page_title="みのり植物共有アプリ Pro", page_icon="🌿", layout="centered")

st.title("🌿 みのり植物共有アプリ")

# --- 3. データの事前読み込み ---
if "display_limit" not in st.session_state:
    st.session_state.display_limit = 10

try:
    # タイムライン用（表示制限件数分だけ取得）
    growth_ref_limit = db.collection("growth_records").order_by("created_at", direction=firestore.Query.DESCENDING).limit(st.session_state.display_limit).stream()
    growth_timeline = list(growth_ref_limit)
    
    # 植物名リスト＆過去ログ用（全件取得）
    growth_all_ref = db.collection("growth_records").order_by("date", direction=firestore.Query.ASCENDING).stream()
    growth_all_list = list(growth_all_ref)
    
    # お世話記録（水やり、雨、肥料）の全件取得
    care_ref = db.collection("care_records").order_by("date", direction=firestore.Query.DESCENDING).stream()
    care_list = list(care_ref)
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
    growth_timeline, growth_all_list, care_list = [], [], []

# 既出の植物名リストを作成
existing_plants = []
for doc in growth_all_list:
    p_name = doc.to_dict().get("plant_name")
    if p_name and p_name not in existing_plants:
        existing_plants.append(p_name)
existing_plants.sort()

# --- 4. ユーザー識別機能 ---
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

if st.session_state.user_name == "":
    st.subheader("👤 最初にあなたの名前を教えてください")
    with st.form("login_form"):
        input_name = st.text_input("ニックネーム（サークルでの呼び名など）", placeholder="例：たろう")
        submit_button = st.form_submit_button("アプリを始める")
        if submit_button:
            if input_name.strip() == "":
                st.error("名前を入力してください！")
            else:
                st.session_state.user_name = input_name
                st.rerun()
else:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"ログイン中: **{st.session_state.user_name}** さん")
    with col2:
        if st.button("名前を変更"):
            st.session_state.user_name = ""
            st.rerun()

    st.markdown("---")

    # 📱 タブの構成
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 タイムライン", "📅 お世話カレンダー", "📝 記録を投稿する", "📖 植物別の過去ログ"])

    # ==========================================
    # タブ1：タイムライン
    # ==========================================
    with tab1:
        st.header("✨ みのりのタイムライン")
        
        if len(growth_timeline) == 0:
            st.info("まだ投稿がありません。「記録を投稿する」タブから最初の投稿をしてみよう！")
        else:
            for doc in growth_timeline:
                g_id = doc.id
                g_data = doc.to_dict()
                
                with st.container(border=True):
                    st.subheader(f"🌱 {g_data.get('plant_name')}")
                    st.caption(f"投稿者: {g_data.get('user_name')} ｜ 日付: {g_data.get('date')}")
                    
                    # 草丈の表示
                    height_val = g_data.get('height')
                    if height_val == "未記録" or height_val is None:
                        st.write("衡量: **草丈未記録**")
                    else:
                        st.metric(label="草丈", value=f"{height_val} cm")
                    
                    if g_data.get('memo'):
                        st.write(f"💬 {g_data.get('memo')}")
                    
                    # 📷 画像表示
                    img_base64 = g_data.get('image', "")
                    if img_base64:
                        img_state_key = f"img_visible_{g_id}"
                        if img_state_key not in st.session_state:
                            st.session_state[img_state_key] = False
                        
                        if not st.session_state[img_state_key]:
                            if st.button("📷 写真を表示する", key=f"btn_open_{g_id}"):
                                st.session_state[img_state_key] = True
                                st.rerun()
                        else:
                            try:
                                st.image(base64.b64decode(img_base64), use_container_width=True)
                                if st.button("❌ 写真を閉じる", key=f"btn_close_{g_id}"):
                                    st.session_state[img_state_key] = False
                                    st.rerun()
                            except:
                                st.warning("画像の表示に失敗しました。")
                    
                    # ーーー リアクション機能 ーーー
                    st.markdown("<br>", unsafe_allow_html=True)
                    reactions = g_data.get("reactions", {"wish": 0, "happy": 0, "thanks": 0, "like": 0, "sad": 0})
                    
                    r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns(5)
                    with r_col1:
                        if st.button(f"✨ {reactions.get('wish', 0)}", key=f"wish_{g_id}", use_container_width=True):
                            reactions['wish'] = reactions.get('wish', 0) + 1
                            db.collection("growth_records").document(g_id).update({"reactions": reactions})
                            st.rerun()
                    with r_col2:
                        if st.button(f"🙌 {reactions.get('happy', 0)}", key=f"happy_{g_id}", use_container_width=True):
                            reactions['happy'] = reactions.get('happy', 0) + 1
                            db.collection("growth_records").document(g_id).update({"reactions": reactions})
                            st.rerun()
                    with r_col3:
                        if st.button(f"🙏 {reactions.get('thanks', 0)}", key=f"thanks_{g_id}", use_container_width=True):
                            reactions['thanks'] = reactions.get('thanks', 0) + 1
                            db.collection("growth_records").document(g_id).update({"reactions": reactions})
                            st.rerun()
                    with r_col4:
                        if st.button(f"👍 {reactions.get('like', 0)}", key=f"like_{g_id}", use_container_width=True):
                            reactions['like'] = reactions.get('like', 0) + 1
                            db.collection("growth_records").document(g_id).update({"reactions": reactions})
                            st.rerun()
                    with r_col5:
                        if st.button(f"😢 {reactions.get('sad', 0)}", key=f"sad_{g_id}", use_container_width=True):
                            reactions['sad'] = reactions.get('sad', 0) + 1
                            db.collection("growth_records").document(g_id).update({"reactions": reactions})
                            st.rerun()

                    # ーーー 💬 コメント機能 ーーー
                    st.markdown("---")
                    st.caption("💬 コメント一覧")
                    
                    comments_ref = db.collection("growth_records").document(g_id).collection("comments").order_by("created_at", direction=firestore.Query.ASCENDING).stream()
                    has_comments = False
                    for c_doc in comments_ref:
                        has_comments = True
                        c_data = c_doc.to_dict()
                        st.markdown(f"**{c_data.get('user_name')}**: {c_data.get('text')} <span style='color:gray; font-size:11px;'>({c_data.get('date')})</span>", unsafe_allow_html=True)
                    
                    if not has_comments:
                        st.caption("まだコメントはありません。")
                    
                    with st.form(key=f"comment_form_{g_id}", clear_on_submit=True):
                        c_text = st.text_input("コメントを入力", placeholder="コメントを書く...", key=f"c_input_{g_id}")
                        if st.form_submit_button("送信"):
                            if c_text.strip() != "":
                                c_data = {
                                    "user_name": st.session_state.user_name,
                                    "text": c_text,
                                    "date": datetime.now().strftime("%m/%d %H:%M"),
                                    "created_at": firestore.SERVER_TIMESTAMP
                                }
                                db.collection("growth_records").document(g_id).collection("comments").add(c_data)
                                st.rerun()

                    # 🗑️ 削除ボタン
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ この投稿を削除する", key=f"del_{g_id}"):
                        db.collection("growth_records").document(g_id).delete()
                        st.success("削除しました！")
                        st.rerun()
            
            # 過去ログ読み込みボタン
            st.markdown("---")
            if st.button("🔽 過去の投稿をもっと見る", use_container_width=True):
                st.session_state.display_limit += 10
                st.rerun()

    # ==========================================
    # タブ2：大画面お世話カレンダー（📱スマホ対応・過去月切り替え版）
    # ==========================================
    with tab2:
        st.header("📅 お世話カレンダー")
        st.write("ボタンを押して今日のお世話を共有しよう！カレンダーに自動でマークがつきます。")
        
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            if st.button("💧 今日、水やりをした！", use_container_width=True):
                db.collection("care_records").add({
                    "user_name": st.session_state.user_name,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "🚰 水やり",
                    "memo": "",
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                st.success("水やりを記録しました！")
                st.rerun()
        with c_col2:
            if st.button("☔ 今日は雨が降った！", use_container_width=True):
                db.collection("care_records").add({
                    "user_name": st.session_state.user_name,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "☔ 雨の日",
                    "memo": "",
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                st.success("雨の日を記録しました！")
                st.rerun()
        
        with st.expander("🧪 肥料をあげた記録を残す"):
            with st.form("fertilizer_form", clear_on_submit=True):
                f_plant = st.selectbox("どの植物にあげましたか？", ["全体・その他"] + existing_plants)
                f_memo = st.text_input("肥料の種類やコメント", placeholder="例：液体肥料を1000倍に薄めて")
                if st.form_submit_button("🧪 肥料記録を保存"):
                    db.collection("care_records").add({
                        "user_name": st.session_state.user_name,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "type": "🧪 肥料",
                        "memo": f"【{f_plant}】 {f_memo}",
                        "created_at": firestore.SERVER_TIMESTAMP
                    })
                    st.success("肥料の記録を保存しました！")
                    st.rerun()

        st.markdown("---")
        
        # ーーー 【改善】年月切り替え機能の追加 ーーー
        now = datetime.now()
        
        # セレクトボックスを横並びにする
        select_year_col, select_month_col = st.columns(2)
        with select_year_col:
            year_options = list(range(2024, now.year + 2))
            selected_year = st.selectbox("年を選択", year_options, index=year_options.index(now.year))
        with select_month_col:
            month_options = list(range(1, 13))
            selected_month = st.selectbox("月を選択", month_options, index=month_options.index(now.month))
        
        st.subheader(f"📅 {selected_year}年 {selected_month}月")
        
        # データの整理
        care_summary = {}
        for doc in care_list:
            item = doc.to_dict()
            c_date = item.get("date")
            c_type = item.get("type", "")
            if c_date:
                if c_date not in care_summary:
                    care_summary[c_date] = set()
                if "水やり" in c_type:
                    care_summary[c_date].add("💧")
                elif "雨" in c_type:
                    care_summary[c_date].add("☔")
                elif "肥料" in c_type:
                    care_summary[c_date].add("🧪")
        
        # ーーー 【改善】スマホでも絶対に崩れないHTML/CSSによる正方形グリッド ーーー
        grid_html = """
        <div style="
            display: grid; 
            grid-template-columns: repeat(7, 1fr); 
            gap: 5px; 
            max-width: 100%; 
            margin: 0 auto;
        ">
        """
        
        # 曜日ヘッダー
        days_header = ["日", "月", "火", "水", "木", "金", "土"]
        for day_name in days_header:
            color = "#e74c3c" if day_name == "日" else ("#3498db" if day_name == "土" else "#555")
            grid_html += f'<div style="text-align: center; font-weight: bold; font-size: 13px; color: {color}; padding-bottom: 5px;">{day_name}</div>'
            
        # カレンダーのオフセット（空白マス）計算
        first_day_of_week, num_days = calendar.monthrange(selected_year, selected_month)
        start_offset = (first_day_of_week + 1) % 7
        
        # 最初の週の空白を埋める
        for _ in range(start_offset):
            grid_html += '<div></div>'
            
        # 各日付のマスを生成
        for day_counter in range(1, num_days + 1):
            date_str = f"{selected_year}-{selected_month:02d}-{day_counter:02d}"
            marks = "".join(list(care_summary.get(date_str, [])))
            
            # 本当に「今日」のマスだけ青枠にする判定（選択した月が今月の場合のみ）
            is_today = (selected_year == now.year and selected_month == now.month and day_counter == now.day)
            bg_color = "#f0f8ff" if is_today else "#ffffff"
            border_style = "2px solid #1e90ff" if is_today else "1px solid #e0e0e0"
            font_weight = "bold" if is_today else "normal"
            
            # aspect-ratio: 1/1 で強制的に正方形を維持、flexで上下にきれいに配置
            grid_html += f"""
            <div style="
                border: {border_style};
                border-radius: 8px;
                padding: 4px 2px;
                background-color: {bg_color};
                text-align: center;
                box-shadow: 1px 1px 3px rgba(0,0,0,0.04);
                aspect-ratio: 1 / 1;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                min-height: 52px;
            ">
                <div style="font-size: 11px; font-weight: {font_weight}; color: #333; line-height: 1;">{day_counter}</div>
                <div style="font-size: 15px; margin-bottom: 2px; line-height: 1.2; min-height: 18px; word-break: break-all;">{marks if marks else '&nbsp;'}</div>
            </div>
            """
            
        grid_html += "</div>"
        st.markdown(grid_html, unsafe_allow_html=True)

    # ==========================================
    # タブ3：記録を投稿する
    # ==========================================
    with tab3:
        st.header("📝 成長記録を投稿する")
        with st.form("upload_form", clear_on_submit=True):
            plant_options = ["🆕 新しい植物を入力する"] + existing_plants
            selected_plant_opt = st.selectbox("🌱 植物を選ぶ", plant_options)
            
            if selected_plant_opt == "🆕 新しい植物を入力する":
                plant_name = st.text_input("新しい植物の名前", placeholder="例：ミニトマト")
            else:
                plant_name = selected_plant_opt
                
            post_date = st.date_input("📅 日付")
            
            has_height = st.checkbox("📏 草丈を記録する", value=True)
            if has_height:
                height = st.number_input("草丈 (cm)", min_value=0.0, max_value=500.0, value=0.0, step=0.1)
            else:
                height = "未記録"
                
            memo = st.text_area("✍️ 状態メモ", placeholder="例：本葉が出てきた！")
            uploaded_file = st.file_uploader("📷 写真を1枚アップロード", type=["jpg", "jpeg", "png"])
            
            if st.form_submit_button("🚀 この内容で投稿する"):
                if plant_name.strip() == "" or plant_name == "🆕 新しい植物を入力する":
                    st.error("植物の名前を入力、または選択してください！")
                else:
                    image_base64 = ""
                    if uploaded_file is not None:
                        img = Image.open(uploaded_file)
                        if img.width > 800:
                            ratio = 800 / float(img.width)
                            img = img.resize((800, int(float(img.height) * float(ratio))), Image.Resampling.LANCZOS)
                        buffer = io.BytesIO()
                        img = img.convert("RGB")
                        img.save(buffer, format="JPEG", quality=80)
                        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    
                    db.collection("growth_records").add({
                        "user_name": st.session_state.user_name,
                        "plant_name": plant_name,
                        "date": post_date.strftime("%Y-%m-%d"),
                        "height": height,
                        "memo": memo,
                        "image": image_base64,
                        "reactions": {"wish": 0, "happy": 0, "thanks": 0, "like": 0, "sad": 0},
                        "created_at": firestore.SERVER_TIMESTAMP
                    })
                    st.success("🎉 成長記録を投稿しました！")
                    st.rerun()

    # ==========================================
    # タブ4：植物別の過去ログ（オンデマンド表示に改善）
    # ==========================================
    with tab4:
        st.header("📖 植物ごとの過去ログ一覧")
        
        if len(existing_plants) == 0:
            st.info("まだ植物のデータがありません。")
        else:
            search_plant = st.selectbox("表示したい植物を選択", existing_plants, key="search_viz")
            
            # ーーー 📝 植物ごとの一言メモ欄の読み込み ーーー
            meta_ref = db.collection("plant_meta").document(search_plant).get()
            meta_data = meta_ref.to_dict() if meta_ref.exists else {}
            
            st.markdown(f"### 📝 「{search_plant}」の一言メモ")
            st.caption("見たい項目を押すと内容が表示されます")
            
            # 【改善】デフォルトでは非表示（重くならないよう、押したら展開するアコーディオン形式に変更）
            with st.expander("🌱 「成長について」のメモを見る"):
                st.info(meta_data.get('growth_comment', '（まだ記入がありません）'))
                
            with st.expander("😋 「おすすめの食べ方」のメモを見る"):
                st.success(meta_data.get('eat_comment', '（まだ記入がありません）'))
            
            # メモの編集用フォーム
            with st.expander("✍️ この植物の一言メモを新しく書く・編集する"):
                with st.form(key=f"meta_form_{search_plant}"):
                    g_comment = st.text_area("成長について（例：水を好む、虫がつきやすい等）", value=meta_data.get('growth_comment', ''))
                    e_comment = st.text_area("こう食べたらおいしかった！（例：サラダ、天ぷらが最高等）", value=meta_data.get('eat_comment', ''))
                    if st.form_submit_button("一言メモを保存・更新"):
                        db.collection("plant_meta").document(search_plant).set({
                            "growth_comment": g_comment,
                            "eat_comment": e_comment,
                            "updated_at": firestore.SERVER_TIMESTAMP
                        }, merge=True)
                        st.success("一言メモを更新しました！")
                        st.rerun()
            
            st.markdown("---")
            st.subheader(f"📖 「{search_plant}」の過去の投稿履歴")
            
            for g in reversed(growth_all_list):
                g_data = g.to_dict()
                if g_data.get("plant_name") == search_plant:
                    with st.container(border=True):
                        st.write(f"📅 **{g_data.get('date')}** （投稿者: {g_data.get('user_name')}）")
                        h = g_data.get('height')
                        st.write(f"📏 草丈: **{h if h == '未記録' else f'{h} cm'}**")
                        if g_data.get('memo'):
                            st.write(f"💬 {g_data.get('memo')}")
                            
                        if g_data.get('image'):
                            img_state_key_tab4 = f"img_visible_tab4_{g.id}"
                            if img_state_key_tab4 not in st.session_state:
                                st.session_state[img_state_key_tab4] = False
                            
                            if not st.session_state[img_state_key_tab4]:
                                if st.button("📷 写真を表示する", key=f"btn_open_tab4_{g.id}"):
                                    st.session_state[img_state_key_tab4] = True
                                    st.rerun()
                            else:
                                try:
                                    st.image(base64.b64decode(g_data.get('image')), use_container_width=True)
                                    if st.button("❌ 写真を閉じる", key=f"btn_close_tab4_{g.id}"):
                                        st.session_state[img_state_key_tab4] = False
                                        st.rerun()
                                except:
                                    pass