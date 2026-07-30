import streamlit as st
import pandas as pd
import csv
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import io
import statistics


st.set_page_config(page_title="Анализ Noshow", page_icon="✈️", layout="wide")

st.title("✈️ Калькулятор NoShow для авиарейсов")
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
                if line.startswith('N4-') and line.count(';') > 10:
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

                # data_list по дню недели теперь хранит: bkd, nsh, segment, den_brd, date
                flights_data = defaultdict(lambda: defaultdict(list))
                all_flights = set()
                flight_segments = defaultdict(Counter)  # частоты сегментов на рейс
                total_rows = 0
                skipped_rows = 0

                # проверка, есть ли колонка Den Brd в файле вообще
                has_den_brd = False

                for row in reader:
                    try:
                        flight_number = row.get('Рейс', '').strip()
                        if not flight_number:
                            skipped_rows += 1
                            continue

                        date_str = row.get('Дата', '')
                        if not date_str:
                            skipped_rows += 1
                            continue

                        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                        day_name = date_obj.strftime('%A')

                        bkd_str = row.get('Seg Bkd Total', '0').strip()
                        nsh_str = row.get('Nsh', '0').strip()
                        den_brd_str = row.get('Den Brd', '0').strip()

                        if 'Den Brd' in row:
                            has_den_brd = True

                        bkd = int(float(bkd_str)) if bkd_str and bkd_str != '' else 0
                        nsh = int(float(nsh_str)) if nsh_str and nsh_str != '' else 0
                        den_brd = int(float(den_brd_str)) if den_brd_str and den_brd_str != '' else 0

                        segment = row.get('Сегмент', '').strip()

                        flights_data[flight_number][day_name].append(
                            {'bkd': bkd, 'nsh': nsh, 'segment': segment, 'den_brd': den_brd, 'date': date_obj}
                        )
                        all_flights.add(flight_number)

                        if segment:
                            flight_segments[flight_number][segment] += 1

                        total_rows += 1

                    except (KeyError, ValueError, TypeError):
                        skipped_rows += 1
                        continue

                st.success(f"✅ Файл успешно обработан! Записей: {total_rows}, Рейсов: {len(all_flights)}"
                           + (f", пропущено строк: {skipped_rows}" if skipped_rows else ""))

                # Порог, ниже которого выборка считается ненадёжной
                MIN_RELIABLE_SAMPLES = 5

                if all_flights:
                    def most_common_segment(flight):
                        counter = flight_segments.get(flight)
                        if counter:
                            return counter.most_common(1)[0][0]
                        return 'Не определен'

                    flight_options = [f"{flight} ({most_common_segment(flight)})" for flight in sorted(all_flights)]

                    selected_flights_with_segments = st.multiselect(
                        "Выберите рейсы для анализа:",
                        flight_options,
                        default=flight_options[:min(5, len(flight_options))]
                    )

                    selected_flights = [flight.split(' (')[0] for flight in selected_flights_with_segments]

                    # Глобальный регулятор агрессивности овербукинга
                    st.sidebar.markdown("### ⚙️ Настройки овербукинга")
                    risk_factor = st.sidebar.slider(
                        "Коэффициент агрессивности овербукинга",
                        min_value=0.3, max_value=1.0, value=0.8, step=0.05,
                        help="1.0 = рекомендовать овербукинг на полный размер прогнозируемого noshow. "
                             "Меньшие значения снижают риск отказа в посадке (Den Brd) ценой части незанятых кресел."
                    )

                    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    russian_days_full = {
                        'Monday': 'Понедельник', 'Tuesday': 'Вторник', 'Wednesday': 'Среда',
                        'Thursday': 'Четверг', 'Friday': 'Пятница', 'Saturday': 'Суббота', 'Sunday': 'Воскресенье'
                    }
                    russian_days_short = {
                        'Monday': 'Пн', 'Tuesday': 'Вт', 'Wednesday': 'Ср', 'Thursday': 'Чт',
                        'Friday': 'Пт', 'Saturday': 'Сб', 'Sunday': 'Вс'
                    }

                    def compute_day_stats(data_list):
                        """Считает rate, среднее bkd, std, кол-во наблюдений и Den Brd статистику по списку записей одного дня."""
                        bkd_values = [d['bkd'] for d in data_list]
                        nsh_values = [d['nsh'] for d in data_list]
                        den_brd_values = [d['den_brd'] for d in data_list]

                        total_bkd = sum(bkd_values)
                        total_nsh = sum(nsh_values)
                        count = len(data_list)

                        rate = total_nsh / total_bkd if total_bkd > 0 else 0.0
                        avg_bookings = total_bkd // count if count else 0

                        # per-flight rate для std (а не общий rate) — чтобы видеть разброс между датами
                        per_flight_rates = [
                            (d['nsh'] / d['bkd']) if d['bkd'] > 0 else 0.0 for d in data_list
                        ]
                        rate_std = statistics.pstdev(per_flight_rates) if count > 1 else 0.0

                        flights_with_den_brd = sum(1 for v in den_brd_values if v > 0)
                        total_den_brd = sum(den_brd_values)
                        den_brd_share = flights_with_den_brd / count if count else 0.0

                        return {
                            'rate': rate,
                            'rate_std': rate_std,
                            'avg_bookings': avg_bookings,
                            'count': count,
                            'total_bkd': total_bkd,
                            'total_nsh': total_nsh,
                            'den_brd_share': den_brd_share,
                            'total_den_brd': total_den_brd,
                            'reliable': count >= MIN_RELIABLE_SAMPLES,
                        }

                    if selected_flights:
                        tabs = st.tabs([f"✈️ {flight}" for flight in selected_flights])

                        for i, flight in enumerate(selected_flights):
                            with tabs[i]:
                                flight_daily_data = flights_data[flight]
                                day_stats = {day: compute_day_stats(data_list)
                                             for day, data_list in flight_daily_data.items() if data_list}
                                flight_segment = most_common_segment(flight)

                                st.subheader(f"📊 Статистика для рейса {flight} {flight_segment}")

                                col1, col2 = st.columns(2)

                                with col1:
                                    st.markdown("**Статистика по дням недели:**")
                                    if day_stats:
                                        for day in days_order:
                                            if day in day_stats:
                                                s = day_stats[day]
                                                reliability_flag = "" if s['reliable'] else " ⚠️ мало данных"
                                                line = (f"**{russian_days_full[day]}**: Rate={s['rate']:.3f} "
                                                        f"(±{s['rate_std']:.3f}), Noshow={s['total_nsh']}, "
                                                        f"Bookings={s['total_bkd']}, Рейсов={s['count']}{reliability_flag}")
                                                st.write(line)
                                                if has_den_brd and s['total_den_brd'] > 0:
                                                    st.caption(
                                                        f"⚠️ Отказано в посадке (Den Brd) в {s['den_brd_share']*100:.0f}% "
                                                        f"рейсов этого дня, всего {s['total_den_brd']} пассажиров — "
                                                        f"признак, что текущий уровень овербукинга уже был рискованным."
                                                    )
                                            else:
                                                st.write(f"**{russian_days_full[day]}**: Нет данных")
                                    else:
                                        st.warning("Нет данных для выбранного рейса")

                                with col2:
                                    st.markdown("**📈 Прогноз на ближайшую неделю:**")
                                    today = datetime.now().date()

                                    if day_stats:
                                        for d in range(7):
                                            future_date = today + timedelta(days=d)
                                            day_name_en = future_date.strftime('%A')
                                            day_name_ru = russian_days_full.get(day_name_en, day_name_en)

                                            s = day_stats.get(day_name_en)
                                            if s:
                                                predicted_noshow = s['avg_bookings'] * s['rate']
                                                reliability_flag = "" if s['reliable'] else " ⚠️"
                                                st.write(f"**{future_date.strftime('%d.%m.%Y')}** ({day_name_ru}) - "
                                                         f"{predicted_noshow:.1f} NoShow{reliability_flag}")
                                            else:
                                                st.write(f"**{future_date.strftime('%d.%m.%Y')}** ({day_name_ru}) - нет данных")
                                    else:
                                        st.warning("Нет данных для прогноза")

                                if day_stats:
                                    max_rate_day = max(day_stats, key=lambda d: day_stats[d]['rate'])
                                    s = day_stats[max_rate_day]

                                    st.subheader("💡 Рекомендации")
                                    reliability_note = "" if s['reliable'] else (
                                        f" ⚠️ Основано всего на {s['count']} наблюдениях — "
                                        f"рекомендуем не полагаться на эту цифру, пока не накопится минимум {MIN_RELIABLE_SAMPLES}."
                                    )
                                    st.info(f"**Самый высокий NoShow rate в {russian_days_full.get(max_rate_day, max_rate_day)}**: "
                                            f"{s['rate']:.3f} ± {s['rate_std']:.3f} ({s['rate']*100:.1f}%){reliability_note}")

                                    recommended_overbooking = int(s['avg_bookings'] * s['rate'] * risk_factor)

                                    st.success(f"**Рекомендуемый овербукинг для {russian_days_full.get(max_rate_day, max_rate_day)}**: "
                                               f"{recommended_overbooking} доп. мест "
                                               f"(при коэффициенте агрессивности {risk_factor:.2f})")

                                    if has_den_brd and s['total_den_brd'] > 0:
                                        st.warning(
                                            f"На этот день недели уже были случаи Den Brd "
                                            f"({s['total_den_brd']} пассажиров). Рекомендуем не увеличивать "
                                            f"коэффициент агрессивности выше текущего."
                                        )

                        st.markdown("---")
                        st.subheader("📋 Сводная таблица по всем рейсам")

                        summary_data = []

                        for flight in selected_flights:
                            flight_daily_data = flights_data[flight]
                            flight_segment = most_common_segment(flight)

                            row_data = {
                                'Рейс': flight,
                                'Сегмент': flight_segment
                            }

                            for day in days_order:
                                if day in flight_daily_data and flight_daily_data[day]:
                                    s = compute_day_stats(flight_daily_data[day])
                                    flag = "" if s['reliable'] else "⚠️"
                                    den_flag = " 🚫" if (has_den_brd and s['total_den_brd'] > 0) else ""
                                    row_data[russian_days_short[day]] = f"{s['rate']:.3f}{flag}{den_flag} (n={s['count']})"
                                else:
                                    row_data[russian_days_short[day]] = "Н/Д"

                            summary_data.append(row_data)

                        if summary_data:
                            summary_df = pd.DataFrame(summary_data)
                            st.dataframe(summary_df, use_container_width=True)
                            st.caption("⚠️ = меньше 5 наблюдений (ненадёжная оценка). "
                                       "🚫 = на этот день недели уже фиксировался отказ в посадке (Den Brd).")

                            csv_summary = summary_df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="📥 Скачать сводную таблицу",
                                data=csv_summary,
                                file_name=f"noshow_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv"
                            )

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

with st.expander("ℹ️ Инструкция по использованию калькулятора"):
    st.markdown("""
    **Заходите в Leonardo**
    - **Отчеты --> Факт вылета --> Выгружаете информацию по всем рейсам, для которых хотите посмотреть NoShow**
    - **Обычно ничего при сохранении менять не надо, но проверьте что файл сохраняется в csv формате с кодировкой Windows-1251**
    - **Загружаете файл сюда**
    - **!!!АХТУНГ!!! Данный анализ лишь прогноз на основе исторических данных за период, выгруженный из Leonardo, окончательное решение об овербукинге принимайте сами**
    - **По хорошему вести отдельный файл и раз в месяц выгружать данные для анализа в него, чтобы выбросы меньше влияли на прогноз. С другой стороны сезонность тоже влияет так что думойте....**
    - **Для защиты данных можно поменять названия/номера рейсов в csv файле на что угодно (ctrl+f)**

    **Что нового в этой версии:**
    - **Учёт Den Brd (отказ в посадке)** — если по историческим данным уже были случаи отказа пассажирам из-за овербукинга, калькулятор явно предупреждает об этом рядом с рекомендацией.
    - **Доверие к оценке (⚠️)** — если по дню недели меньше 5 наблюдений, оценка помечается как ненадёжная, чтобы не переоценивать точность прогноза на малой выборке.
    - **Разброс (± std)** — рядом со средним noshow rate показывается разброс между рейсами, чтобы видеть, насколько стабильна оценка.
    - **Регулятор агрессивности овербукинга** — слайдер в боковой панели позволяет вручную снижать рекомендованный овербукинг относительно "чистого" прогноза, компенсируя асимметрию рисков (пустое кресло дешевле отказа в посадке).
    - **Сегмент рейса теперь определяется как самый частый маршрут**, а не первый попавшийся — на случай, если один номер рейса летал по разным маршрутам в разные дни.
    """)
