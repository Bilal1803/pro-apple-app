import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import random

# --- НАСТРОЙКА ИНТЕРФЕЙСА ---
st.set_page_config(page_title="Pro Apple ERP v5", page_icon="🍏", layout="wide")

# Подключение к базе
conn = sqlite3.connect('pro_apple_v5.db', check_same_thread=False)
c = conn.cursor()

# Создаем таблицу
c.execute('''CREATE TABLE IF NOT EXISTS inventory 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              date_added TEXT, category TEXT, model TEXT, 
              specs TEXT, color TEXT, imei TEXT, description TEXT,
              buy_price REAL, sell_price REAL, acc_name TEXT, acc_price REAL,
              status TEXT, manager TEXT, date_sold TEXT)''')
conn.commit()

# --- ФУНКЦИЯ ИГРЫ (Вынесена отдельно) ---
def run_apple_tycoon():
    st.title("🎮 Pro Apple Tycoon")
    st.sidebar.markdown("---")
    st.sidebar.info("Цель: Стать Техно-Магнатом, накопив 50 млн ₽")

    if 'game_money' not in st.session_state:
        st.session_state.game_money = 500000
        st.session_state.game_rep = 50
        st.session_state.game_log = ["🚀 Вы вышли на охоту за айфонами!"]

    money = st.session_state.game_money
    if money < 1000000:
        rank, next_r, color = "📦 Перекуп с Авито", 1000000, "gray"
    elif money < 5000000:
        rank, next_r, color = "🏪 Хозяин точки", 5000000, "blue"
    elif money < 15000000:
        rank, next_r, color = "🏢 Владелец офиса", 15000000, "green"
    else:
        rank, next_r, color = "👑 Техно-Магнат", None, "red"

    st.subheader(f"Ваш ранг: :{color}[{rank}]")
    if next_r:
        st.progress(min(money / next_r, 1.0))
        st.caption(f"До следующего уровня осталось: {next_r - money:,.0f} ₽")

    stat1, stat2 = st.columns(2)
    stat1.metric("Ваш Капитал", f"{money:,.0f} ₽")
    stat2.metric("Репутация", f"{st.session_state.game_rep}%")

    st.write("### Управление бизнесом")
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("📱 Сделка дня"):
            chance = 0.4 + (st.session_state.game_rep / 200)
            if random.random() < chance:
                profit = random.randint(40000, 150000)
                st.session_state.game_money += profit
                st.session_state.game_log.insert(0, f"✅ Продали товар! +{profit:,.0f} ₽")
            else:
                loss = random.randint(30000, 80000)
                st.session_state.game_money -= loss
                st.session_state.game_rep -= 5
                st.session_state.game_log.insert(0, f"❌ Неудачная сделка! -{loss:,.0f} ₽")
            st.rerun()

    with c2:
        if st.button("📢 Реклама (50к)"):
            if st.session_state.game_money >= 50000:
                st.session_state.game_money -= 50000
                st.session_state.game_rep = min(st.session_state.game_rep + 10, 100)
                st.session_state.game_log.insert(0, "📢 Реклама запущена!")
                st.rerun()
            else:
                st.error("Нет денег!")

    with c3:
        if st.button("🔄 Сброс игры"):
            st.session_state.game_money = 500000
            st.session_state.game_rep = 50
            st.session_state.game_log = ["Игра началась заново."]
            st.rerun()

    st.write("---")
    for msg in st.session_state.game_log[:3]:
        st.write(f"• {msg}")

# --- СИСТЕМА ВХОДА ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🍏 Pro Apple Management</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        user = st.text_input("Логин")
        pw = st.text_input("Пароль", type="password")
        if st.button("Войти", use_container_width=True):
            if user == "admin" and pw == "123":
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Доступ запрещен")
else:
    # --- ГЛАВНОЕ МЕНЮ ---
    main_menu = st.sidebar.radio("Разделы приложения", ["📦 Управление магазином", "🎮 Игра Tycoon"])

    if main_menu == "🎮 Игра Tycoon":
        run_apple_tycoon()

    elif main_menu == "📦 Управление магазином":
        # Подменю для склада (чтобы не загромождать боковую панель)
        tab_menu = st.radio("Действие:", ["📊 Дашборд", "➕ Приемка", "📦 Склад", "💰 Продажа", "📜 История"], horizontal=True)

        if tab_menu == "📊 Дашборд":
            st.header("Аналитика")
            df_all = pd.read_sql_query("SELECT * FROM inventory", conn)
            sold_df = df_all[df_all['status'] == 'Продано']
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("На складе", len(df_all[df_all['status'] == 'В наличии']))
            with c2:
                profit = (sold_df['sell_price'].fillna(0) + sold_df['acc_price'].fillna(0) - sold_df['buy_price'].fillna(0)).sum()
                st.metric("Чистая прибыль", f"{profit:,.0f} ₽")
            with c3:
                st.metric("Сделок", len(sold_df))

        elif tab_menu == "➕ Приемка":
            st.header("Приемка")
            with st.form("add_form"):
                col1, col2 = st.columns(2)
                with col1:
                    cat = st.selectbox("Категория", ["iPhone", "iPad", "MacBook", "AirPods", "Watch", "Samsung", "Dyson"])
                    model = st.text_input("Модель")
                    imei = st.text_input("IMEI")
                with col2:
                    color = st.text_input("Цвет")
                    buy_p = st.number_input("Цена закупки", min_value=0)
                    desc = st.text_area("Описание")
                
                if st.form_submit_button("Добавить"):
                    now = datetime.now().strftime("%d.%m.%Y %H:%M")
                    c.execute("INSERT INTO inventory (date_added, category, model, color, imei, description, buy_price, status) VALUES (?,?,?,?,?,?,?,?)",
                              (now, cat, model, color, imei, desc, buy_p, "В наличии"))
                    conn.commit()
                    st.success("Добавлено!")

        elif tab_menu == "📦 Склад":
            st.header("Склад")
            df_stock = pd.read_sql_query("SELECT date_added, category, model, color, imei, description, buy_price FROM inventory WHERE status = 'В наличии'", conn)
            st.dataframe(df_stock, use_container_width=True)

        elif tab_menu == "💰 Продажа":
            st.header("Продажа")
            items = pd.read_sql_query("SELECT id, model, imei FROM inventory WHERE status = 'В наличии'", conn)
            if not items.empty:
                item_id = st.selectbox("Товар", items['id'], format_func=lambda x: f"{items[items['id']==x]['model'].values[0]} ({items[items['id']==x]['imei'].values[0]})")
                p_sell = st.number_input("Цена продажи")
                a_name = st.text_input("Аксессуар")
                a_price = st.number_input("Цена допа")
                if st.button("Продать"):
                    date = datetime.now().strftime("%d.%m.%Y %H:%M")
                    c.execute("UPDATE inventory SET status='Продано', sell_price=?, acc_name=?, acc_price=?, date_sold=? WHERE id=?", 
                              (p_sell, a_name, a_price, date, item_id))
                    conn.commit()
                    st.balloons()
            else:
                st.warning("Товаров нет")

        elif tab_menu == "📜 История":
            st.header("История")
            df_sold = pd.read_sql_query("SELECT * FROM inventory WHERE status = 'Продано'", conn)
            st.write(df_sold)
