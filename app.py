import streamlit as st
import pandas as pd
import csv
from datetime import datetime, timedelta
from collections import defaultdict
import io

st.set_page_config(page_title="Анализ Noshow by Кирилл", page_icon="✈️", layout="wide")

# Заголовок приложения
st.title("✈️ Анализатор Noshow для авиарейсов")
st.markdown("---")

# Загрузка файла
uploaded_file = st.file_uploader("Загрузите CSV файл с данными рейсов", type=['csv'])

if uploaded_file is not None:
    try:
        # Пробуем разные кодировки
        encodings_to_try = ['utf-8-sig', 'windows-1251', 'cp1251', 'iso-8859-1', 'utf-8']
        
        content = None
        used_encoding = None
        
        for encoding in encodings_to_try:
            try:
                uploaded_file.seek(0)
                content = uploaded_file.getvalue().decode(encoding)
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            uploaded_file.seek(0)
            content = uploaded_file.getvalue().decode('utf-8', errors='replace')
            used_encoding = 'utf-8 (with errors replaced)'
        
        # Пропускаем первые строки до начала данных
        lines = content.split('\n')
        
        # Ищем строку с заголовками
        header_line_index = -1
        for i, line in enumerate(lines):
            if 'Рейс;Дата;Частота' in line or 'Рейс;Дата' in line:
                header_line_index = i
                break
            if line.startswith('N4-281') and ';' in line:
                header_line_index = i - 2 if i >= 2 else 0
                break
        
        if header_line_index == -1:
            for i, line in enumerate(lines):
                if ';' in line and ('Рейс' in line or 'Дата' in line or 'Seg Bkd Total' in line):
                    header_line_index = i
                    break
        
        if header_line_index >= 0:
            data_lines = lines[header_line_index:]
            data_lines = [line.strip() for line in data_lines if line.strip() and not line.replace(';', '').strip() == '']
            
            if len(data_lines) > 1:
                csv_content = '\n'.join(data_lines)
                csv_file = io.StringIO(csv_content)
                reader = csv.DictReader(csv_file, delimiter=';')
                
                flights_data = defaultdict(lambda: defaultdict(list))
                all_flights = set()
                total_rows = 0
                
                for row in reader:
                    try:
                        flight_number = row.get('Рейс', '').strip()
                        if not flight_number:
                            continue
                            
                        date_str = row.get('Дата', '')
                        if not date_str:
                            continue
                            
                        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                        day_name = date_obj.strftime('%A')
                        
                        bkd_str = row.get('Seg Bkd Total', '0').strip()
                        nsh_str = row.get('Nsh', '0').strip()
                        
                        bkd = int(float(bkd_str)) if bkd_str and bkd_str != '' else 0
                        nsh = int(float(nsh_str)) if nsh_str and nsh_str != '' else 0
                        
                        segment = row.get('Сегмент', '').strip()
                        
                        flights_data[flight_number][day_name].append((bkd, nsh, segment))
                        all_flights.add(flight_number)
                        total_rows += 1
                            
                    except (KeyError, ValueError, TypeError):
                        continue
                
                st.success(f"✅ Файл успешно обработан! Записей: {total_rows}, Рейсов: {len(all_flights)}")
                
                if all_flights:
                    selected_flight = st.selectbox("Выберите рейс для анализа:", sorted(all_flights))
                    
                    if selected_flight:
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
                        
                        if flight_segment is None:
                            flight_segment = "Не определен"
                        
                        # Статистика
                        st.subheader(f"📊 Статистика для рейса {selected_flight} {flight_segment}")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Статистика по дням недели:**")
                            if weekly_noshow_rate:
                                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                                russian_days = {
                                    'Monday': 'Понедельник',
                                    'Tuesday': 'Вторник', 
                                    'Wednesday': 'Среда',
                                    'Thursday': 'Четверг',
                                    'Friday': 'Пятница',
                                    'Saturday': 'Суббота',
                                    'Sunday': 'Воскресенье'
                                }
                                
                                for day in days_order:
                                    if day in weekly_noshow_rate:
                                        rate = weekly_noshow_rate[day]
                                        total_bkd = sum(bkd for bkd, nsh, seg in flight_daily_data[day])
                                        total_nsh = sum(nsh for bkd, nsh, seg in flight_daily_data[day])
                                        count = len(flight_daily_data[day])
                                        
                                        st.write(f"**{russian_days[day]}**: Rate={rate:.3f}, Noshow={total_nsh}, Bookings={total_bkd}, Рейсов={count}")
                            else:
                                st.warning("Нет данных для выбранного рейса")
                        
                        with col2:
                            st.markdown("**📈 Прогноз на ближайшую неделю:**")
                            today = datetime.now().date()
                            
                            if weekly_noshow_rate:
                                russian_days = {
                                    'Monday': 'Понедельник',
                                    'Tuesday': 'Вторник', 
                                    'Wednesday': 'Среда',
                                    'Thursday': 'Четверг',
                                    'Friday': 'Пятница',
                                    'Saturday': 'Суббота',
                                    'Sunday': 'Воскресенье'
                                }
                                
                                for i in range(7):
                                    future_date = today + timedelta(days=i)
                                    day_name_en = future_date.strftime('%A')
                                    day_name_ru = russian_days.get(day_name_en, day_name_en)
                                    
                                    rate = weekly_noshow_rate.get(day_name_en, 0)
                                    avg_bookings = weekly_avg_bookings.get(day_name_en, 200)
                                    predicted_noshow = avg_bookings * rate
                                    
                                    date_type = "🎯 СЕГОДНЯ" if i == 0 else f"через {i} дн."
                                    
                                    st.write(f"**{future_date.strftime('%d.%m.%Y')}** ({day_name_ru}) - {predicted_noshow:.1f} noshow")
                            else:
                                st.warning("Нет данных для прогноза")
                        
                        # Рекомендации
                        if weekly_noshow_rate:
                            max_rate_day = max(weekly_noshow_rate, key=weekly_noshow_rate.get)
                            max_rate = weekly_noshow_rate[max_rate_day]
                            
                            russian_days = {
                                'Monday': 'Понедельник',
                                'Tuesday': 'Вторник', 
                                'Wednesday': 'Среда',
                                'Thursday': 'Четверг',
                                'Friday': 'Пятница',
                                'Saturday': 'Суббота',
                                'Sunday': 'Воскресенье'
                            }
                            
                            st.subheader("💡 Рекомендации")
                            st.info(f"**Самый высокий noshow rate в {russian_days.get(max_rate_day, max_rate_day)}**: {max_rate:.3f} ({max_rate*100:.1f}%)")
                            
                            avg_bookings_max_day = weekly_avg_bookings.get(max_rate_day, 200)
                            recommended_overbooking = int(avg_bookings_max_day * max_rate)
                            
                            st.success(f"**Рекомендуемый овербукинг для {russian_days.get(max_rate_day, max_rate_day)}**: {recommended_overbooking} дополнительных мест")
                else:
                    st.error("❌ Не найдено данных о рейсах в файле")
            else:
                st.error("❌ Не найдено данных в файле")
        else:
            st.error("❌ Не удалось найти заголовки данных в файле")
                
    except Exception as e:
        st.error(f"❌ Ошибка при обработке файла: {e}")

else:
    st.info("👆 Пожалуйста, загрузите CSV файл для начала анализа")

# Инструкция
with st.expander("ℹ️ Инструкция по формату файла"):
    st.markdown("""
    **Требуемые колонки в CSV файле:**
    - **Рейс** - номер рейса
    - **Дата** - дата в формате DD.MM.YYYY  
    - **Сегмент** - маршрут (например: LED-KGD)
    - **Seg Bkd Total** - количество бронирований
    - **Nsh** - количество неявившихся пассажиров (noshow)

    **Пример корректного формата:**
    ```
    Рейс;Дата;Сегмент;Seg Bkd Total;Nsh
    N4-281;01.09.2025;LED-KGD;216;6
    N4-281;02.09.2025;LED-KGD;192;7
    ```
    """)
