import streamlit as st
import pandas as pd
import csv
from datetime import datetime, timedelta
from collections import defaultdict
import io
#Россия - священная наша держава,
#Россия - любимая наша страна.
#Могучая воля, великая слава -
#Твое достоянье на все времена!
#Славься, Отечество наше свободное,
#Братских народов союз вековой,
#Предками данная мудрость народная!
#Славься, страна! Мы гордимся тобой!
#От южных морей до полярного края
#Раскинулись наши леса и поля.
#Одна ты на свете! Одна ты такая -
#Хранимая Богом родная земля!
#Славься, Отечество наше свободное,
#Братских народов союз вековой,
#Предками данная мудрость народная!
#Славься, страна! Мы гордимся тобой!
#Широкий простор для мечты и для жизни
#Грядущие нам открывают года.
#Нам силу дает наша верность Отчизне.
#Так было, так есть и так будет всегда!
#Славься, Отечество наше свободное,
#Братских народов союз вековой,
#Предками данная мудрость народная!
#Славься, страна! Мы гордимся тобой!
st.set_page_config(page_title="Анализ Noshow by Кирилл", page_icon="✈️", layout="wide")


st.title("✈️ Анализатор/Калькулятор Noshow для авиарейсов by Кирилл")
st.markdown("---")


uploaded_file = st.file_uploader("Загрузите CSV файл с данными рейсов", type=['csv'])

if uploaded_file is not None:
    try:
        encodings_to_try = ['utf-8-sig', 'windows-1251', 'cp1251', 'iso-8859-1', 'utf-8']
        
        content = None
        
        for encoding in encodings_to_try:
            try:
                uploaded_file.seek(0)
                content = uploaded_file.getvalue().decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            uploaded_file.seek(0)
            content = uploaded_file.getvalue().decode('utf-8', errors='replace')

        lines = content.split('\n')
        
        data_start_index = -1
        for i, line in enumerate(lines):
            if 'Рейс;Дата;Частота;Сегмент;' in line:
                data_start_index = i
                break
        
        if data_start_index == -1:
            for i, line in enumerate(lines):
                if line.startswith('N4-281') and line.count(';') > 10:
                    data_start_index = i - 1
                    break
        
        if data_start_index >= 0 and data_start_index + 1 < len(lines):
            header_line = lines[data_start_index].strip()
            data_lines = lines[data_start_index + 1:]
            
            data_lines = [line.strip() for line in data_lines if line.strip() and line.count(';') > 5]
            
            if data_lines:
                csv_content = header_line + '\n' + '\n'.join(data_lines)
                
                csv_file = io.StringIO(csv_content)
                reader = csv.DictReader(csv_file, delimiter=';')
                
                flights_data = defaultdict(lambda: defaultdict(list))
                all_flights = set()
                total_rows = 0
                
                for row in reader:
                    try:
                        flight_number = row.get('Рейс', '').strip()
                        if not flight_number or flight_number == 'N4-281, 01.09.25 - 07.10.25, All':
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
            st.error("❌ Не удалось найти данные в файле")
                
    except Exception as e:
        st.error(f"❌ Ошибка при обработке файла: {e}")

else:
    st.info("👆 Пожалуйста, загрузите CSV файл для начала анализа")

# Инструкция
with st.expander("ℹ️ Инструкция по использованию калькулятора"):
    st.markdown("""
    **Заходите в Leonardo**
    - **Отчеты --> Факт вылета --> Выгружаете по отдельному рейсу информацию за максимальный период(на момент написания макс до 01.09.25)**
    - **Обычно ничего при сохранении менять не надо, но проверьте что файл сохраняется в csv формате с кодировкой Windows-1251** 
    - **Загружаете файл сюда**
    - **!!!АХТУНГ!!! Данный анализ лишь прогноз на основе исторических данных за период, выгруженный из Leonardo, окончательное решение об овербукинге принимайте сами**
    - **По хорошему вести отдельный файл и раз в месяц выгружать данные для анализа в него, чтобы выбросы меньше влияли на прогноз. С другой стороны сезонность тоже влияет так что думойте....**
    
    """)
