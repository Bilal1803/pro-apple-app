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
    menu = st.sidebar.radio("Навигация", ["📊 Дашборд", "📦 Склад", "➕ Приемка", "💰 Оформить продажу", "📜 История продаж"])
    
    if st.sidebar.button("Выйти"):
        st.session_state.auth = False
        st.rerun()

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
            st.dataframe(df_sold, use_container_width=True)
            st.info(f"Всего заработано чистыми: {df_sold['Прибыль'].sum():,.0f} ₽")
        else:
            st.write("Продаж пока не было.")