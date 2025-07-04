import os
from flask import Flask, render_template, request, make_response, redirect, url_for, jsonify
import requests
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO
import re
import sys
from pathlib import Path

# Решение проблемы с путями при упаковке в exe
if getattr(sys, 'frozen', False):
    # Если приложение 'заморожено' (упаковано)
    template_dir = Path(sys._MEIPASS) / 'templates'
    static_dir = Path(sys._MEIPASS)  / 'static'
else:
    # Обычный режим разработки
    template_dir = Path(__file__).parent / 'app' / 'templates'
    static_dir = Path(__file__).parent / 'app' / 'static'
app = Flask(__name__, 
            template_folder=str(template_dir),
            static_folder=str(static_dir))

load_dotenv()


# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', "-1002302463734")

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email)

def validate_phone(phone):
    pattern = r'^(\+7|8)[0-9]{10}$'
    return re.match(pattern, phone)

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
    except Exception as e:
        app.logger.error(f"Ошибка отправки в Telegram: {e}")

def send_telegram_notification(params, optimal, client_ip, download_data=None, link_clicked=False):
    try:
        ip_info = requests.get(f"http://ip-api.com/json/{client_ip}?fields=country,city,isp").json()
        city = ip_info.get('city', 'Неизвестно')
        country = ip_info.get('country', 'Неизвестно')
        
        if link_clicked:
            message = (
                "🔗 *Кликнули по ссылке на сайт*\n\n"
                f"📅 *Дата:* {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"🌍 *Локация:* {city}, {country}\n"
                f"📡 *IP:* `{client_ip}`"
            )
            if download_data:
                message += (
                    "\n\n📥 *Данные пользователя:*\n"
                    f"🏢 *Компания:* {download_data['company']}\n"
                    f"👤 *Должность:* {download_data['position']}\n"
                    f"📞 *Телефон:* {download_data['phone']}\n"
                    f"✉️ *Email:* {download_data['email']}"
                )
        else:
            message = (
                "🚛 *Новый расчет системы мониторинга транспорта*\n\n"
                f"📅 *Дата:* {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"🌍 *Локация:* {city}, {country}\n"
                f"📡 *IP:* `{client_ip}`\n\n"
                f"🔢 *Параметры расчета:*\n"
                f"- Парк техники: {params['fleet_size']} ед.\n"
                f"- Поломок оборудования: {params['breakdowns_per_year']} на ТС\n"
                f"- АО плата: {params['ao_cost']} руб./мес\n\n"
                f"🏆 *Оптимальный вариант:* {optimal['description']}\n"
                f"💵 *Годовые затраты:* {format_number(optimal['next_years'])} руб."
            )
            
            if download_data:
                message += (
                    "\n\n📥 *Данные скачаны:*\n"
                    f"🏢 *Компания:* {download_data['company']}\n"
                    f"👤 *Должность:* {download_data['position']}\n"
                    f"📞 *Телефон:* {download_data['phone']}\n"
                    f"✉️ *Email:* {download_data['email']}"
                )
        
        send_telegram_message(message)
    except Exception as e:
        app.logger.error(f"Ошибка отправки уведомления: {e}")

def format_number(x):
    return "{:,.0f}".format(x).replace(",", " ")

def generate_excel(params, options, optimal):
    output = BytesIO()
    
    try:
        # Создаем DataFrame с результатами
        data = []
        
        # Добавляем заголовок
        data.append(["Результаты расчета системы мониторинга транспорта"])
        data.append([])
        
        # Добавляем параметры расчета
        data.append(["Параметры расчета:"])
        data.append(["Размер парка техники (ед.):", params.get('fleet_size', 0)])
        data.append(["Количество поломок оборудования на 1 ТС в год:", params.get('breakdowns_per_year', 0)])
        data.append(["Доля сервисных выездов в городе (%):", params.get('city_share', 0) * 100])
        data.append(["Стоимость замены оборудования (руб.):", params.get('equipment_cost', 0)])
        data.append(["Процент замены оборудования (%):", params.get('replacement_rate', 0) * 100])
        data.append(["Абонентская плата за 1 ТС (руб./мес):", params.get('ao_cost', 0)])
        data.append(["Средняя стоимость сервисного выезда в городе (руб.):", params.get('service_cost_city', 0)])
        data.append(["Средняя стоимость сервисного выезда вне города (руб.):", params.get('service_cost_outside', 0)])
        data.append(["Стоимость лицензии на 1 ТС (руб.):", params.get('license_cost', 0)])
        data.append(["Годовая поддержка ПО (%):", params.get('software_support_rate', 0) * 100])
        data.append(["Количество специалистов:", params.get('specialists_count', 0)])
        data.append(["Зарплата специалиста (руб./мес):", params.get('specialist_salary', 0)])
        data.append(["Зарплата администратора сервера (руб./мес):", params.get('server_admin_salary', 0)])
        data.append(["Расходники на 1 выезд (руб.):", params.get('consumables_cost', 0)])
        data.append([])
        
        # Добавляем сравнение вариантов
        data.append(["Сравнение вариантов:"])
        data.append(["Вариант", "Первый год (руб.)", "Последующие годы (руб./год)", "Оптимальный"])
        
        for key, option in options.items():
            data.append([
                option.get('description', ''),
                option.get('first_year', 0),
                option.get('next_years', 0),
                'Да' if key == optimal[0] else 'Нет'
            ])
        
        data.append([])
        
        # Добавляем детализацию оптимального варианта
        data.append(["Детализация оптимального варианта:"])
        data.append(["Статья затрат", "Сумма (руб.)"])
        
        for item, value in optimal[1].get('details', {}).items():
            data.append([item, value])
        
        # Создаем DataFrame из собранных данных
        df = pd.DataFrame(data)
        
        # Записываем в Excel
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Результаты', index=False, header=False)
            
            # Настраиваем ширину столбцов
            worksheet = writer.sheets['Результаты']
            worksheet.column_dimensions['A'].width = 40
            worksheet.column_dimensions['B'].width = 20
            worksheet.column_dimensions['C'].width = 25
            worksheet.column_dimensions['D'].width = 15
            
            # Форматируем заголовки
            for row in worksheet.iter_rows(min_row=1, max_row=1):
                for cell in row:
                    cell.font = cell.font.copy(bold=True)
            
            for row in [3, 17, 19 + len(options)]:
                for cell in worksheet[row]:
                    cell.font = cell.font.copy(bold=True)

        output.seek(0)
        return output

    except Exception as e:
        app.logger.error(f"Error generating Excel: {str(e)}")
        raise

def calculate_options(params):
    options = {}
    breakdowns_total = params['fleet_size'] * params['breakdowns_per_year']
    replacements_total = breakdowns_total * params['replacement_rate']
    replacements_cost = replacements_total * params['equipment_cost']
    server_admin_cost = params['server_admin_salary'] * 1.3 * 12
    
    ao_subscription = params['fleet_size'] * params['ao_cost'] * 12
    service_city = breakdowns_total * params['city_share'] * params['service_cost_city']
    service_outside = breakdowns_total * (1 - params['city_share']) * params['service_cost_outside']
    
    options['ao_contractor'] = {
        'first_year': ao_subscription + service_city + service_outside + replacements_cost,
        'next_years': ao_subscription + service_city + service_outside + replacements_cost,
        'description': "Абонентское обслуживание + подрядчики",
        'details': {
            'Абонентская плата': ao_subscription,
            'Выезды подрядчиков': service_city + service_outside,
            'Замена оборудования': replacements_cost
        },
        'pros': [
            "Минимальные стартовые затраты",
            "Не нужны свои специалисты",
            "Обслуживание включено в АО"
        ],
        'cons': [
            "Зависимость от подрядчика",
            "Риск роста цен на обслуживание",
            "Меньший контроль над системой"
        ]
    }
    
    specialists_cost = params['specialists_count'] * params['specialist_salary'] * 1.3 * 12
    consumables = breakdowns_total * params['consumables_cost']
    
    options['ao_inhouse'] = {
        'first_year': ao_subscription + specialists_cost + replacements_cost + consumables,
        'next_years': ao_subscription + specialists_cost + replacements_cost + consumables,
        'description': "Абонентское обслуживание + свои специалисты",
        'details': {
            'Абонентская плата': ao_subscription,
            'Зарплата специалистов': specialists_cost,
            'Замена оборудования': replacements_cost,
            'Расходники': consumables
        },
        'pros': [
            "Полный контроль над оборудованием",
            "Быстрое реагирование на проблемы",
            "Гибкость в управлении"
        ],
        'cons': [
            "Высокие затраты на персонал",
            "Нужно обучать сотрудников",
            "Административная нагрузка"
        ]
    }
    
    license_cost = params['fleet_size'] * params['license_cost']
    software_support = license_cost * params['software_support_rate']
    
    options['license_inhouse'] = {
        'first_year': license_cost + server_admin_cost + specialists_cost + replacements_cost + consumables + software_support,
        'next_years': server_admin_cost + specialists_cost + replacements_cost + consumables + software_support,
        'description': "Бессрочные лицензии ПО + свои специалисты",
        'details': {
            'Лицензии (разово)': license_cost,
            'Администратор сервера': server_admin_cost,
            'Зарплата специалистов': specialists_cost,
            'Замена оборудования': replacements_cost,
            'Расходники': consumables,
            'Поддержка ПО': software_support
        },
        'pros': [
            "Полная независимость",
            "Единоразовые затраты на лицензии",
            "Максимальная кастомизация"
        ],
        'cons': [
            "Высокие стартовые затраты",
            "Необходимость содержать штат",
            "Ответственность за оборудование"
        ]
    }
    
    options['license_contractor'] = {
        'first_year': license_cost + server_admin_cost + service_city + service_outside + replacements_cost + software_support,
        'next_years': server_admin_cost + service_city + service_outside + replacements_cost + software_support,
        'description': "Бессрочные лицензии ПО + подрядчики",
        'details': {
            'Лицензии (разово)': license_cost,
            'Администратор сервера': server_admin_cost,
            'Выезды подрядчиков': service_city + service_outside,
            'Замена оборудования': replacements_cost,
            'Поддержка ПО': software_support
        },
        'pros': [
            "Оптимальный баланс затрат",
            "Не нужны свои ремонтники",
            "Контроль над ПО"
        ],
        'cons': [
            "Зависимость от подрядчиков",
            "Доп. затраты на админа",
            "Риск некачественного ремонта"
        ]
    }
    
    return options


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        params = {
            'fleet_size': int(request.form.get('fleet_size', 0)),
            'ao_cost': float(request.form.get('ao_cost', 0)),
            'breakdowns_per_year': float(request.form.get('breakdowns_per_year', 0)),
            'city_share': float(request.form.get('city_share', 0)) / 100,
            'service_cost_city': float(request.form.get('service_cost_city', 0)),
            'service_cost_outside': float(request.form.get('service_cost_outside', 0)),
            'equipment_cost': float(request.form.get('equipment_cost', 0)),
            'replacement_rate': float(request.form.get('replacement_rate', 0)) / 100,
            'license_cost': float(request.form.get('license_cost', 0)),
            'software_support_rate': float(request.form.get('software_support_rate', 0)) / 100,
            'specialists_count': int(request.form.get('specialists_count', 0)),
            'specialist_salary': float(request.form.get('specialist_salary', 0)),
            'server_admin_salary': float(request.form.get('server_admin_salary', 0)),
            'consumables_cost': float(request.form.get('consumables_cost', 0))
        }
        
        options = calculate_options(params)
        optimal = min(options.items(), key=lambda x: x[1]['next_years'])
        
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if TELEGRAM_BOT_TOKEN:
            send_telegram_notification(params, optimal[1], client_ip.split(',')[0].strip())
        
        return render_template('result.html', 
                            params=params, 
                            options=options, 
                            optimal=optimal,
                            format_number=format_number)
    
    default_params = {
        'fleet_size': 600,
        'ao_cost': 500,
        'breakdowns_per_year': 1,
        'city_share': 80,
        'service_cost_city': 2500,
        'service_cost_outside': 3250,
        'equipment_cost': 20000,
        'replacement_rate': 10,
        'license_cost': 5000,
        'software_support_rate': 10,
        'specialists_count': 4,
        'specialist_salary': 120000,
        'server_admin_salary': 90000,
        'consumables_cost': 500
    }
    
    return render_template('form.html', params=default_params)

@app.route('/download', methods=['POST'])
def download_excel():
    try:
        # Валидация данных
        required_fields = ['company', 'position', 'phone', 'email']
        user_data = {field: request.form.get(field, '').strip() for field in required_fields}
        
        for field in required_fields:
            if not user_data[field]:
                return jsonify({"error": f"Поле '{field}' обязательно для заполнения"}), 400

        if not validate_phone(user_data['phone']):
            return jsonify({"error": "Некорректный номер телефона. Используйте формат +79998887766 или 89998887766"}), 400
            
        if not validate_email(user_data['email']):
            return jsonify({"error": "Некорректный email адрес"}), 400

        # Получаем параметры из формы
        params = {
            'fleet_size': int(request.form.get('fleet_size', 0)),
            'ao_cost': float(request.form.get('ao_cost', 0)),
            'breakdowns_per_year': float(request.form.get('breakdowns_per_year', 0)),
            'city_share': float(request.form.get('city_share', 0)) / 100,
            'service_cost_city': float(request.form.get('service_cost_city', 0)),
            'service_cost_outside': float(request.form.get('service_cost_outside', 0)),
            'equipment_cost': float(request.form.get('equipment_cost', 0)),
            'replacement_rate': float(request.form.get('replacement_rate', 0)) / 100,
            'license_cost': float(request.form.get('license_cost', 0)),
            'software_support_rate': float(request.form.get('software_support_rate', 0)) / 100,
            'specialists_count': int(request.form.get('specialists_count', 0)),
            'specialist_salary': float(request.form.get('specialist_salary', 0)),
            'server_admin_salary': float(request.form.get('server_admin_salary', 0)),
            'consumables_cost': float(request.form.get('consumables_cost', 0))
        }

        options = calculate_options(params)
        optimal = min(options.items(), key=lambda x: x[1]['next_years'])
        
        # Генерируем Excel (без данных пользователя)
        excel_file = generate_excel(params, options, optimal)
        
        # Отправляем уведомление в Telegram с данными пользователя
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if TELEGRAM_BOT_TOKEN:
            send_telegram_notification(params, optimal[1], client_ip.split(',')[0].strip(), user_data)
        
        # Возвращаем файл
        response = make_response(excel_file.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=monitoring_calculation.xlsx'
        return response
        
    except Exception as e:
        app.logger.error(f"Error in download_excel: {str(e)}")
        return jsonify({"error": f"Ошибка при генерации файла: {str(e)}"}), 500

@app.route('/feedback', methods=['POST'])
def feedback():
    try:
        feedback_data = {
            'company': request.form.get('company', '').strip(),
            'name': request.form.get('name', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'email': request.form.get('email', '').strip(),
            'message': request.form.get('message', '').strip()
        }
        
        # Проверка обязательных полей
        required_fields = ['company', 'name', 'phone', 'email', 'message']
        for field in required_fields:
            if not feedback_data[field]:
                return jsonify({"error": f"Поле '{field}' обязательно для заполнения"}), 400
        
        if not validate_phone(feedback_data['phone']):
            return jsonify({"error": "Некорректный номер телефона. Используйте формат +79998887766 или 89998887766"}), 400
            
        if not validate_email(feedback_data['email']):
            return jsonify({"error": "Некорректный email адрес"}), 400
        
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        if TELEGRAM_BOT_TOKEN:
            message = (
                "📣 *Новое сообщение обратной связи*\n\n"
                f"🏢 *Компания:* {feedback_data['company']}\n"
                f"👤 *Контактное лицо:* {feedback_data['name']}\n"
                f"📞 *Телефон:* {feedback_data['phone']}\n"
                f"✉️ *Email:* {feedback_data['email']}\n"
                f"🌐 *IP:* {client_ip}\n\n"
                f"📝 *Сообщение:*\n{feedback_data['message']}"
            )
            send_telegram_message(message)
        
        return jsonify({"success": "Ваше сообщение успешно отправлено! Мы свяжемся с вами в ближайшее время."})
    except Exception as e:
        app.logger.error(f"Error in feedback: {str(e)}")
        return jsonify({"error": f"Ошибка при отправке сообщения: {str(e)}"}), 500

@app.route('/link_clicked', methods=['POST'])
def link_clicked():
    try:
        user_data = {
            'company': request.form.get('company', ''),
            'position': request.form.get('position', ''),
            'phone': request.form.get('phone', ''),
            'email': request.form.get('email', '')
        }
        
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        if TELEGRAM_BOT_TOKEN:
            send_telegram_notification(None, None, client_ip.split(',')[0].strip(), 
                                     user_data if any(user_data.values()) else None, 
                                     link_clicked=True)
        
        return jsonify({"status": "success"})
    except Exception as e:
        app.logger.error(f"Error in link_clicked: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
else:
    application = app  # Для совместимости с WSGI