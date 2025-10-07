import streamlit as st
import pandas as pd
import csv
from datetime import datetime, timedelta
from collections import defaultdict
import io

st.set_page_config(page_title="Анализ Noshow", page_icon="✈️", layout="wide")

# Заголовок приложения
st.title("✈️ Анализатор Noshow для авиарейсов")
st.markdown("---")

# Загрузка файла
uploaded_file = st.file_uploader("Загрузите CSV файл с данными рейсов", type=['csv'])

if uploaded_file is not None:
    try:
        # Показываем содержимое файла для отладки
        content = uploaded_file.getvalue().decode('utf-8')
        st.text_area("Содержимое файла (первые 500 символов):", content[:500], height=150)
        
        # Автоматическое определение разделителя
        first_line = content.split('\n')[0]
        st.write(f"Первая строка файла: {first_line}")
        
        delimiter = ';' if ';' in first_line else ','
        st.write(f"Определен разделитель: '{delimiter}'")
        
        # Чтение данных
        flights_data = defaultdict(lambda: defaultdict(list))
        all_flights = set()
        total_rows = 0
        processed_rows = 0
        
        # Создаем StringIO для csv.reader
        csv_file = io.StringIO(content)
        
        # Показываем заголовки
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        st.write(f"Заголовки файла: {reader.fieldnames}")
        
        # Сбрасываем указатель
        csv_file.seek(0)
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        
        problematic_rows = []
        
        for row_num, row in enumerate(reader, 1):
            try:
                # Отладочная информация
                if row_num <= 3:  # Показываем первые 3 строки
                    st.write(f"Строка {row_num}: {dict(list(row.items())[:5])}")
                
                # Проверяем наличие обязательных полей
                if not row.get('Flight') or not row.get('Date'):
                    problematic_rows.append(f"Строка {row_num}: отсутствуют обязательные поля")
                    continue
                
                flight_number = row['Flight'].strip()
                date_str = row['Date'].strip()
                
                # Пропускаем пустые строки
                if not flight_number or not date_str:
                    continue
                
                date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                day_name = date_obj.strftime('%A')
                
                # Пытаемся получить числовые значения
                bkd_str = row.get('seg_bkd_total', '0').strip()
                nsh_str = row.get('noshow', '0').strip()
                
                # Заменяем пустые значения на 0
                bkd = int(bkd_str) if bkd_str and bkd_str.isdigit() else 0
                nsh = int(nsh_str) if nsh_str and nsh_str.isdigit() else 0
                
                segment = row.get('Segment', '').strip()
                
                flights_data[flight_number][day_name].append((bkd, nsh, segment))
                all_flights.add(flight_number)
                total_rows += 1
                processed_rows += 1
                    
            except ValueError as e:
                problematic_rows.append(f"Строка {row_num}: ошибка значения - {e}")
                continue
            except Exception as e:
                problematic_rows.append(f"Строка {row_num}: непредвиденная ошибка - {e}")
                continue
        
        # Показываем результаты обработки
        st.success(f"✅ Обработка завершена!")
        st.write(f"Всего строк в файле: {row_num}")
        st.write(f"Успешно обработано: {processed_rows}")
        st.write(f"Проблемных строк: {len(problematic_rows)}")
        
        if problematic_rows:
            with st.expander("Показать проблемные строки"):
                for problem in problematic_rows[:10]:  # Показываем первые 10 проблем
                    st.write(problem)
        
        if all_flights:
            st.success(f"✅ Найдено рейсов: {len(all_flights)}")
            st.write(f"Список рейсов: {', '.join(sorted(all_flights))}")
            
            # Селектор рейса
            selected_flight = st.selectbox("Выберите рейс для анализа:", sorted(all_flights))
            
            if selected_flight:
                # Анализ выбранного рейса
                flight_daily_data = flights_data[selected_flight]
                weekly_noshow_rate = {}
                weekly_avg_bookings = {}
                flight_segment = None
                
                st.write(f"Данные для рейса {selected_flight}: {len(flight_daily_data)} дней")
                
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
            st.error("❌ В файле не найдено данных о рейсах. Проверьте формат файла.")
    
    except Exception as e:
        st.error(f"❌ Критическая ошибка при обработке файла: {e}")
        st.info("Попробуйте загрузить другой файл или проверьте формат данных")

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
    
    **Поддерживаемые разделители:** запятая (,) или точка с запятой (;)
    """)

# Кнопка для сброса
if st.button("🔄 Загрузить другой файл"):
    st.rerun()
