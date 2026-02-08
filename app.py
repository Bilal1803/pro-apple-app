import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- НАСТРОЙКА ИНТЕРФЕЙСА ---
st.set_page_config(page_title="Pro Apple ERP v5", page_icon="🍏", layout="wide")

# Подключение к базе (новая версия для поддержки описаний и допов)
conn = sqlite3.connect('pro_apple_v5.db', check_same_thread=False)
c = conn.cursor()

# Создаем расширенную таблицу
c.execute('''CREATE TABLE IF NOT EXISTS inventory 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              date_added TEXT, category TEXT, model TEXT, 
              specs TEXT, color TEXT, imei TEXT, description TEXT,
              buy_price REAL, sell_price REAL, acc_name TEXT, acc_price REAL,
              status TEXT, manager TEXT, date_sold TEXT)''')
conn.commit()

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
    # --- МЕНЮ ---
   # Было:
# menu = st.sidebar.radio("Меню", ["Склад", "Продажа"])

# Сделай так:
menu = st.sidebar.radio("Разделы приложения", ["📦 Склад и Учет", "🎮 Игра Tycoon"])

if menu == "📦 Склад и Учет":
    # Тут весь твой старый код склада (приемка, таблицы и т.д.)
    st.write("Ваш основной функционал") 

elif menu == "🎮 Игра Tycoon":
    run_apple_tycoon() # Просто вызываем функцию, которую вставили в конце

    # --- ВКЛАДКА: ДАШБОРД ---
    if menu == "📊 Дашборд":
        st.header("Аналитика магазина")
        df_all = pd.read_sql_query("SELECT * FROM inventory", conn)
        sold_df = df_all[df_all['status'] == 'Продано']
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Товаров на складе", len(df_all[df_all['status'] == 'В наличии']))
        with c2:
            # Считаем прибыль: (ЦенаПродажи + ЦенаДопа) - ЦенаЗакупки
            profit = (sold_df['sell_price'].fillna(0) + sold_df['acc_price'].fillna(0) - sold_df['buy_price'].fillna(0)).sum()
            st.metric("Чистая прибыль", f"{profit:,.0f} ₽")
        with c3:
            st.metric("Всего сделок", len(sold_df))

    # --- ВКЛАДКА: ПРИЕМКА ---
    elif menu == "➕ Приемка":
        st.header("Приемка нового товара")
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cat = st.selectbox("Категория", ["iPhone", "iPad", "MacBook", "AirPods", "Watch", "Samsung", "Dyson"])
                model = st.text_input("Модель и объем памяти")
                imei = st.text_input("IMEI или Серийный номер")
            with col2:
                color = st.text_input("Цвет")
                buy_p = st.number_input("Цена закупки", min_value=0)
                desc = st.text_area("Описание (АКБ, нюансы, комплект)")
            
            if st.form_submit_button("Добавить на склад"):
                now = datetime.now().strftime("%d.%m.%Y %H:%M")
                c.execute("INSERT INTO inventory (date_added, category, model, color, imei, description, buy_price, status) VALUES (?,?,?,?,?,?,?,?)",
                          (now, cat, model, color, imei, desc, buy_p, "В наличии"))
                conn.commit()
                st.success(f"{model} добавлен!")

    # --- ВКЛАДКА: СКЛАД ---
    elif menu == "📦 Склад":
        st.header("Товары в наличии")
        search = st.text_input("🔍 Поиск по модели или IMEI")
        df_stock = pd.read_sql_query("SELECT date_added, category, model, color, imei, description, buy_price FROM inventory WHERE status = 'В наличии'", conn)
        if search:
            df_stock = df_stock[df_stock.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
        st.dataframe(df_stock, use_container_width=True)

    # --- ВКЛАДКА: ПРОДАЖА ---
    elif menu == "💰 Оформить продажу":
        st.header("Новая сделка")
        items = pd.read_sql_query("SELECT id, model, imei FROM inventory WHERE status = 'В наличии'", conn)
        
        if not items.empty:
            item_choice = st.selectbox("Выберите устройство", items['id'].tolist(), 
                                       format_func=lambda x: f"{items.loc[items['id']==x, 'model'].values[0]} ({items.loc[items['id']==x, 'imei'].values[0]})")
            
            st.subheader("Детали сделки")
            c1, c2, c3 = st.columns(3)
            with c1:
                price_sell = st.number_input("Цена за устройство", min_value=0)
            with c2:
                acc_name = st.text_input("Доп. аксессуар", placeholder="Напр: Чехол + Стекло")
            with c3:
                acc_price = st.number_input("Цена за аксессуар", min_value=0)
            
            if st.button("🤝 Подтвердить продажу", use_container_width=True):
                sold_date = datetime.now().strftime("%d.%m.%Y %H:%M")
                c.execute("UPDATE inventory SET status='Продано', sell_price=?, acc_name=?, acc_price=?, date_sold=? WHERE id=?", 
                          (price_sell, acc_name, acc_price, sold_date, item_choice))
                conn.commit()
                st.balloons()
                st.success(f"Продано! Общая сумма: {price_sell + acc_price} ₽")
        else:
            st.warning("На складе пусто")

    # --- ВКЛАДКА: ИСТОРИЯ ПРОДАЖ ---
    elif menu == "📜 История продаж":
        st.header("Архив проданных товаров")
        df_sold = pd.read_sql_query("""SELECT date_sold, category, model, imei, buy_price, 
                                       sell_price, acc_name, acc_price FROM inventory 
                                       WHERE status = 'Продано'""", conn)
        
        if not df_sold.empty:
            # Считаем прибыль для каждой строки для наглядности
            df_sold['Прибыль'] = (df_sold['sell_price'] + df_sold['acc_price']) - df_sold['buy_price']

          import random

def run_apple_tycoon():
    st.title("🎮 Pro Apple Tycoon")
    st.sidebar.markdown("---")
    st.sidebar.info("Цель: Стать Техно-Магнатом, накопив 50 млн ₽")

    # Инициализация игровых данных в памяти браузера
    if 'game_money' not in st.session_state:
        st.session_state.game_money = 500000
        st.session_state.game_rep = 50
        st.session_state.game_log = ["🚀 Вы вышли на охоту за айфонами!"]

    # Логика рангов
    money = st.session_state.game_money
    if money < 1000000:
        rank, next_r, color = "📦 Перекуп с Авито", 1000000, "gray"
    elif money < 5000000:
        rank, next_r, color = "🏪 Хозяин точки", 5000000, "blue"
    elif money < 15000000:
        rank, next_r, color = "🏢 Владелец офиса", 15000000, "green"
    else:
        rank, next_r, color = "👑 Техно-Магнат", None, "red"

    # Отображение прогресса
    st.subheader(f"Ваш ранг: :{color}[{rank}]")
    if next_r:
        st.progress(min(money / next_r, 1.0))
        st.caption(f"До следующего уровня осталось: {next_r - money:,.0f} ₽")

    # Панель приборов
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
                st.session_state.game_log.insert(0, f"✅ Продали iPhone 15 Pro! +{profit:,.0f} ₽")
            else:
                loss = random.randint(30000, 80000)
                st.session_state.game_money -= loss
                st.session_state.game_rep -= 5
                st.session_state.game_log.insert(0, f"❌ Клиент вернул товар! -{loss:,.0f} ₽")
            st.rerun()

    with c2:
        if st.button("📢 Реклама (50к)"):
            if st.session_state.game_money >= 50000:
                st.session_state.game_money -= 50000
                st.session_state.game_rep = min(st.session_state.game_rep + 10, 100)
                st.session_state.game_log.insert(0, "📢 Запустили рекламу в Instagram! Репутация +10")
                st.rerun()
            else:
                st.error("Нет денег!")

    with c3:
        if st.button("🔄 Сброс"):
            st.session_state.game_money = 500000
            st.session_state.game_rep = 50
            st.session_state.game_log = ["Игра началась заново."]
            st.rerun()

    st.write("---")
    st.write("**События:**")
    for msg in st.session_state.game_log[:3]:
        st.write(f"• {msg}")
      
