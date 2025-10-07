import streamlit as st
import pandas as pd
import csv
from datetime import datetime, timedelta
from collections import defaultdict
import io

st.set_page_config(page_title="Анализ Noshow by Кирилл", page_icon="✈️", layout="wide")

# Заголовок приложения
st.title("✈️ Анализатор Noshow для авиарейсов by Кирилл")
st.markdown("---")

# Загрузка файла
uploaded_file = st.file_uploader("Загрузите CSV файл с данными рейсов", type=['csv'])

if uploaded_file is not None:
    try:
        # Чтение файла с обработкой BOM
        content = uploaded_file.getvalue().decode('utf-8-sig')
        
        # Автоматическое определение разделителя
        first_line = content.split('\n')[0]
        delimiter = ';' if ';' in first_line else ','
        
        # Чтение данных
        flights_data = defaultdict(lambda: defaultdict(list))
        all_flights = set()
        total_rows = 0
        
        # Создаем StringIO для csv.reader
        csv_file = io.StringIO(content)
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        
        for row in reader:
            try:
                flight_number = row['Flight'].strip()
                date_obj = datetime.strptime(row['Date'], '%d.%m.%Y')
                day_name = date_obj.strftime('%A')
                bkd = int(row['seg_bkd_total'])
                nsh = int(row['noshow'])
                segment = row['Segment'].strip()
                
                flights_data[flight_number][day_name].append((bkd, nsh, segment))
                all_flights.add(flight_number)
                total_rows += 1
                    
            except (KeyError, ValueError):
                continue
        
        st.success(f"✅ Файл успешно обработан! Записей: {total_rows}, Рейсов: {len(all_flights)}")
        
        if all_flights:
            # Селектор рейса
            selected_flight = st.selectbox("Выберите рейс для анализа:", sorted(all_flights))
            
            if selected_flight:
                # Анализ выбранного рейса
                flight_daily_data = flights_data[selected_flight]
                weekly_noshow_rate = {}
                weekly_avg_bookings = {}
                flight_segment = None
                
                for day, data_list in flight_daily_data.items():
                    if not data_list:
                        continue
                        
                    total_bkd_day = 0
                    total_nsh_day = 0
                    
                    if flight_segment is None and data_list:
                        flight_segment = data_list[0][2]
                    
                    for bkd, nsh, segment in data_list:
                        total_bkd_day += bkd
                        total_nsh_day += nsh
                    
                    if total_bkd_day > 0:
                        weekly_noshow_rate[day] = total_nsh_day / total_bkd_day
                    else:
                        weekly_noshow_rate[day] = 0.0
                        
                    weekly_avg_bookings[day] = total_bkd_day // len(data_list) if data_list else 0
                
                # Сегмент по умолчанию
                if flight_segment is None:
                    flight_segment = "Не определен"
                
                # Статистика
                st.subheader(f"📊 Статистика для рейса {selected_flight} {flight_segment}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Статистика по дням недели:**")
                    if weekly_noshow_rate:
                        for day, rate in sorted(weekly_noshow_rate.items()):
                            total_bkd = sum(bkd for bkd, nsh, seg in flight_daily_data[day])
                            total_nsh = sum(nsh for bkd, nsh, seg in flight_daily_data[day])
                            count = len(flight_daily_data[day])
                            
                            st.write(f"**{day}**: Rate={rate:.3f}, Noshow={total_nsh}, Bookings={total_bkd}, Рейсов={count}")
                    else:
                        st.warning("Нет данных для выбранного рейса")
                
                with col2:
                    # Прогноз на неделю
                    st.markdown("**📈 Прогноз на ближайшую неделю:**")
                    today = datetime.now().date()
                    
                    if weekly_noshow_rate:
                        for i in range(7):
                            future_date = today + timedelta(days=i)
                            day_name = future_date.strftime('%A')
                            
                            rate = weekly_noshow_rate.get(day_name, 0)
                            avg_bookings = weekly_avg_bookings.get(day_name, 200)
                            predicted_noshow = avg_bookings * rate
                            
                            date_type = "🎯 СЕГОДНЯ" if i == 0 else f"через {i} дн."
                            
                            st.write(f"**{future_date.strftime('%d.%m.%Y')}** ({day_name}) - {predicted_noshow:.1f} noshow")
                    else:
                        st.warning("Нет данных для прогноза")
                
                # Рекомендации
                if weekly_noshow_rate:
                    max_rate_day = max(weekly_noshow_rate, key=weekly_noshow_rate.get)
                    min_rate_day = min(weekly_noshow_rate, key=weekly_noshow_rate.get)
                    max_rate = weekly_noshow_rate[max_rate_day]
                    
                    st.subheader("💡 Рекомендации")
                    st.info(f"**Самый высокий noshow rate в {max_rate_day}**: {max_rate:.3f} ({max_rate*100:.1f}%)")
                    
                    avg_bookings_max_day = weekly_avg_bookings.get(max_rate_day, 200)
                    recommended_overbooking = int(avg_bookings_max_day * max_rate)
                    
                    st.success(f"**Рекомендуемый овербукинг для {max_rate_day}**: {recommended_overbooking} дополнительных мест")
        else:
            st.error("❌ В файле не найдено данных о рейсах")
    
    except Exception as e:
        st.error(f"❌ Ошибка при обработке файла: {e}")

else:
    st.info("👆 Пожалуйста, загрузите CSV файл для начала анализа")

# Инструкция
with st.expander("ℹ️ Инструкция по формату файла"):
    st.markdown("""
    Файл CSV должен содержать следующие колонки:
    - **Flight** - номер рейса
    - **Date** - дата в формате DD.MM.YYYY
    - **Segment** - маршрут
    - **seg_bkd_total** - количество бронирований
    - **noshow** - количество неявившихся пассажиров
    
    Пример структуры:
    ```
    Flight;Date;Segment;seg_bkd_total;noshow
    N4-281;01.09.2025;LED-KGD;216;6
    N4-281;02.09.2025;LED-KGD;192;7
    ```
    """)
