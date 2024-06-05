import telebot
import requests
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
bot = telebot.TeleBot('6745338320:AAGnckRGajcNcvkfkTUrWP_8Qo9z3Cvz_t0')

GeoapifyApiKey = "c91ab8f84d2a42e985f6989c202900bb"
Latitude = "50.4501"
Longitude = "30.5234"
Radius = 1000

def create_database():
    conn = sqlite3.connect('places.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS places
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT, address TEXT)''')
    conn.commit()
    conn.close()


def update_database():
    try:
        places = get_city_places_async("tourism")  # Получаем все места
        conn = sqlite3.connect('places.db')
        c = conn.cursor()

        # Очищаем таблицу перед обновлением
        c.execute("DELETE FROM places")

        for place in places:
            name = place['Name']
            address = place['AddressLine2']
            category = ', '.join(place['Categories'])
            c.execute("INSERT INTO places (name, category, address) VALUES (?, ?, ?)", (name, category, address))

        # Добавляем отладочный вывод
        c.execute("SELECT * FROM places")
        rows = c.fetchall()
        print("Вміст бази даних після оновлення:")
        for row in rows:
            print(row)

        conn.commit()
        conn.close()

    except Exception as ex:
        print(f"Помилка під час оновлення бази даних: {ex}")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Вітання! Введіть /place_by_name для пошуку місця за назвою, /place_by_address для пошуку місця за його адресою, /list_places для списку місць, /update_place для оновлення місця, /add_place для додавання нового місця, або /delete_place для видалення місця.")

@bot.message_handler(commands=['place_by_name'])
def ask_for_name(message):
    bot.reply_to(message, "Введіть назву місця:")
    bot.register_next_step_handler(message, get_place_by_name)

def get_place_by_name(message):
    place_name = message.text
    place_info = get_place_info_by_name(place_name)
    if place_info:
        response_message = f"Адреса місця '{place_name}': {place_info}"
    else:
        response_message = f"Місце з назвою '{place_name}' не знайдено у базі даних."
    bot.reply_to(message, response_message)

def get_place_info_by_name(place_name):
    conn = sqlite3.connect('places.db')
    c = conn.cursor()
    c.execute("SELECT address FROM places WHERE name=?", (place_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

@bot.message_handler(commands=['place_by_address'])
def ask_for_address(message):
    bot.reply_to(message, "Введіть адресу місця:")
    bot.register_next_step_handler(message, get_place_by_address)

def get_place_by_address(message):
    address = message.text
    place_info = get_place_info_by_address(address)
    if place_info:
        response_message = f"Місце за адресою '{address}': {place_info}"
    else:
        response_message = f"Інформація про місце за адресою '{address}' не знайдено у базі даних."
    bot.reply_to(message, response_message)

def get_place_info_by_address(address):
    conn = sqlite3.connect('places.db')
    c = conn.cursor()
    c.execute("SELECT name FROM places WHERE address=?", (address,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

@bot.message_handler(commands=['list_places'])
def ask_for_category(message):
    bot.reply_to(message, "Введіть категорію місця  (tourism, park, entertainment)")
    bot.register_next_step_handler(message, list_places)

def list_places(message):
    category = message.text
    places = get_places_from_db_by_category(category)

    response_message = ""
    if places:
        for place in places:
            response_message += f"Name: {place[1]}\n"
            response_message += f"Address: {place[3]}\n\n"
    else:
        response_message = f"Неможливо знайти місця для категорії '{category}'."

    bot.reply_to(message, response_message)

def get_places_from_db_by_category(category):
    conn = sqlite3.connect('places.db')
    c = conn.cursor()
    c.execute("SELECT * FROM places WHERE category LIKE ?", ('%' + category + '%',))
    result = c.fetchall()
    conn.close()
    return result

def get_city_places_async(category):
    url = f"https://api.geoapify.com/v2/places?categories={category}&filter=circle:{Longitude},{Latitude},{Radius}&apiKey={GeoapifyApiKey}"
    response = requests.get(url)
    response.raise_for_status()

    place_response = response.json()
    if place_response and 'features' in place_response:
        sorted_places = sorted(place_response['features'], key=lambda x: len(x['properties']['categories']), reverse=True)

        return [{
            'Name': place['properties']['name'],
            'Categories': place['properties']['categories'],
            'AddressLine2': place['properties']['address_line2']
        } for place in sorted_places]

    return []

@bot.message_handler(commands=['update_place'])
def ask_for_update_name(message):
    bot.reply_to(message, "Введіть назву місця, яку потрібно оновити:")
    bot.register_next_step_handler(message, get_update_details)

def get_update_details(message):
    global update_name
    update_name = message.text
    bot.reply_to(message, "Введіть нову адресу місця:")
    bot.register_next_step_handler(message, update_place_info)

def update_place_info(message):
    try:
        new_address = message.text

        conn = sqlite3.connect('places.db')
        c = conn.cursor()
        c.execute("UPDATE places SET address = ? WHERE name = ?", (new_address, update_name))
        conn.commit()
        conn.close()

        bot.reply_to(message, f"Адреса місця '{update_name}' успішно оновлена!")
    except Exception as e:
        bot.reply_to(message, f"Помилка при оновленні інформації про місце: {e}")

@bot.message_handler(commands=['add_place'])
def ask_for_place_name(message):
    bot.reply_to(message, "Введіть назву нового місця:")
    bot.register_next_step_handler(message, ask_for_place_category)

def ask_for_place_category(message):
    global new_place_name
    new_place_name = message.text
    bot.reply_to(message, "Введіть категорію нового місця:")
    bot.register_next_step_handler(message, ask_for_place_address)

def ask_for_place_address(message):
    global new_place_category
    new_place_category = message.text
    bot.reply_to(message, "Введіть адресу нового місця:")
    bot.register_next_step_handler(message, add_new_place)

def add_new_place(message):
    try:
        new_place_address = message.text

        conn = sqlite3.connect('places.db')
        c = conn.cursor()
        c.execute("INSERT INTO places (name, category, address) VALUES (?, ?, ?)", (new_place_name, new_place_category, new_place_address))
        conn.commit()
        conn.close()

        bot.reply_to(message, f"Місце '{new_place_name}' успішно додано!")
    except Exception as e:
        bot.reply_to(message, f"Помилка при додаванні нового місця: {e}")

@bot.message_handler(commands=['delete_place'])
def ask_for_delete_name(message):
    bot.reply_to(message, "Введіть назву місця, яку ви бажаєте видалити:")
    bot.register_next_step_handler(message, delete_place_by_name)

def delete_place_by_name(message):
    place_name = message.text
    if delete_place_from_db(place_name):
        response_message = f"Місце з назвою '{place_name}' успішно видалено з бази даних."
    else:
        response_message = f"Місце з назвою '{place_name}' не знайдено у базі даних."
    bot.reply_to(message, response_message)

def delete_place_from_db(place_name):
    conn = sqlite3.connect('places.db')
    c = conn.cursor()
    c.execute("DELETE FROM places WHERE name=?", (place_name,))
    rows_affected = c.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

# Flask Routes
@app.route('/add_place', methods=['POST'])
def add_place():
    try:
        data = request.json
        name = data['name']
        category = data['category']
        address = data['address']

        conn = sqlite3.connect('places.db')
        c = conn.cursor()
        c.execute("INSERT INTO places (name, category, address) VALUES (?, ?, ?)", (name, category, address))
        conn.commit()
        conn.close()

        return jsonify({"message": "Місце успішно додано!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# GET route to get place by name
@app.route('/place_by_name/<name>', methods=['GET'])
def get_place_by_name_route(name):
    place_info = get_place_info_by_name(name)
    if place_info:
        return jsonify({"address": place_info}), 200
    else:
        return jsonify({"error": "Place not found"}), 404

# GET route to get place by address
@app.route('/place_by_address/<address>', methods=['GET'])
def get_place_by_address_route(address):
    place_info = get_place_info_by_address(address)
    if place_info:
        return jsonify({"name": place_info}), 200
    else:
        return jsonify({"error": "Place not found"}), 404

# GET route to list places by category
@app.route('/list_places/<category>', methods=['GET'])
def list_places_route(category):
    places = get_places_from_db_by_category(category)
    if places:
        return jsonify([{"name": place[1], "category": place[2], "address": place[3]} for place in places]), 200
    else:
        return jsonify({"error": "No places found for this category"}), 404

# PUT route to update place by name
@app.route('/update_place/<name>', methods=['PUT'])
def update_place_route(name):
    data = request.json
    new_address = data.get('address')
    if new_address:
        try:
            conn = sqlite3.connect('places.db')
            c = conn.cursor()
            c.execute("UPDATE places SET address = ? WHERE name = ?", (new_address, name))
            conn.commit()
            conn.close()
            return jsonify({"message": f"Place '{name}' updated successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Invalid input"}), 400

# DELETE route to delete place by name
@app.route('/delete_place/<name>', methods=['DELETE'])
def delete_place_route(name):
    if delete_place_from_db(name):
        return jsonify({"message": f"Place '{name}' deleted successfully"}), 200
    else:
        return jsonify({"error": "Place not found"}), 404

if __name__ == "__main__":
    create_database()
    update_database()  # Обновляем базу данных при запуске
    bot.polling(none_stop=True)
    app.run(port=5000)
