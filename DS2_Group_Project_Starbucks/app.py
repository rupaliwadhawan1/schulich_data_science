from flask import Flask
from flask import request, jsonify,render_template, url_for, session
import speech_recognition as sr
from gtts import gTTS
import pygame
import os
import time

import pandas as pd

confirmed_order = None

app = Flask(__name__)
app.secret_key = 'your_secret_key' 

pygame.mixer.init()

# Base menu items
menu_items = [
    "Espresso", "Cappuccino", "Latte", "Americano", "Mocha", 
    "Flat White", "Macchiato", "Caramel Macchiato", "Frappuccino", 
    "Shaken Espresso", "Tea", "Hot Chocolate"
]

# Hot or iced drinks
hot_or_cold = ["Hot", "Iced"]

# Cup size options
cup_sizes = ["Short", "Tall", "Grande", "Venti"]

# Types of milk
milk_types = ["None", "2% Milk", "Half and Half", "Whole Milk", "Skim Milk", "Coconut Milk", "Almond Milk", "Soy Milk", "Oat Milk"]

# Types of toppings
toppings = ["None", "Drizzle", "Whipped Cream", "Cold Foam", "Cinnamon Powder", "Chocolate Powder"]

# Number of extra espresso shots 
extra_shots = ["0", "1", "2", "3", "4", "5"]

# Types of syrup
syrups = ["None", "Vanilla", "Caramel", "Hazelnut", "Peppermint", "Classic", "Mocha"]


@app.route('/')
def home():
    return render_template('menu.html')

def construct_order_summary(parsed_order):
    order_summary_parts = []

    for quantity, item in parsed_order['items']:
        item_summary = [f"{quantity} {item}"]

        if parsed_order['sizes']:
            item_summary.append(' '.join(parsed_order['sizes']))
        if parsed_order['milks'] and parsed_order['milks'][0] != 'None':
            item_summary.append("with " + ' and '.join(parsed_order['milks']))
        if parsed_order['syrups'] and parsed_order['syrups'][0] != 'None':
            item_summary.append("with " + ' and '.join(parsed_order['syrups']))
        if parsed_order['toppings'] and parsed_order['toppings'][0] != 'None':
            item_summary.append("with " + ' and '.join(parsed_order['toppings']))
        if parsed_order['extra_shots']:
            extra_shots_summary = "with " + ' and '.join(parsed_order['extra_shots']) + " extra shot(s)"
            item_summary.append(extra_shots_summary)

        order_summary_parts.append(' '.join(item_summary))

    return ', '.join(order_summary_parts)

import random

def calculate_price(order_components):
    total_price = 0.0

    for quantity, item_name in order_components['items']:
        base_price = random.uniform(2.5, 4.5)
        size_price = 0
        if order_components.get('sizes') and len(order_components['sizes']) > 0:
            size_price = {"Short": 0, "Tall": 0.5, "Grande": 1, "Venti": 1.5}.get(order_components['sizes'][0], 0)

        topping_price = 0.5 if 'toppings' in order_components and order_components['toppings'] and order_components['toppings'][0] != "None" else 0

        extra_shot_price = 0.5 * sum(int(shot) for shot in order_components.get('extra_shots', []) if shot.isdigit())

        syrup_price = 0.3 if 'syrups' in order_components and order_components['syrups'] and order_components['syrups'][0] != "None" else 0

        item_total_price = (base_price + size_price + topping_price + extra_shot_price + syrup_price) * quantity
        total_price += item_total_price

    return total_price

@app.route('/voice_order')
def main():
    recognizer = sr.Recognizer()

    microphone = sr.Microphone()

    speak_text("Welcome to Starbucks! What would you like to order today?")

    full_order = ""
    total_price = 0.0

    while True:
        with sr.Microphone() as source:
            if not full_order:
                spoken_order = recognize_speech(recognizer, source)
                if spoken_order:
                    parsed_order = parse_order_nlp(spoken_order)

                    if parsed_order['items']:
                        total_price = calculate_price(parsed_order)
                        full_order = construct_order_summary(parsed_order)
                        audio_url = speak_text(f"Your current order is: {full_order}. Is this correct? Please say 'Yes' to confirm or 'No' to re-order.")
                    else:
                        audio_url = speak_text("Sorry, we don't have that item. Please try ordering again.")
                        continue
                else:
                    continue

            confirmation_response = recognize_speech(recognizer, source)

            if confirmation_response and "yes" in confirmation_response.lower():
                audio_url = speak_text("Would you like to add anything else to your order? Please say 'Yes' to add more or 'No' to finalize the order.")
                add_more_response = recognize_speech(recognizer, source)

                if add_more_response and "yes" in add_more_response.lower():
                    audio_url = speak_text("What would you like to add?")
                    additional_order = recognize_speech(recognizer, source)
                    if additional_order:
                        additional_parsed_order = parse_order_nlp(additional_order)
                        if additional_parsed_order['items']:
                            total_price += calculate_price(additional_parsed_order)
                            additional_order_summary = construct_order_summary(additional_parsed_order)
                            full_order += " and " + additional_order_summary
                            audio_url = speak_text(f"Your updated order is: {full_order}. Is this correct? Please say 'Yes' to confirm or 'No' to modify.")
                        else:
                            audio_url = speak_text("Sorry, we don't have that item. Please try ordering something else.")
                    else:
                        continue
                elif add_more_response and "no" in add_more_response.lower():
                    session['confirmed_order'] = full_order
                    session['total_price'] = total_price
                    break
            elif confirmation_response and "no" in confirmation_response.lower():
                full_order = ""
                continue
            else:
                audio_url = speak_text("Sorry, I didn't catch that. Please try again.")
                
    print(f"Thanks! Your final order is: {full_order}. The total price is ${total_price:.2f}. Have a great day!")
    speak_text(f"Thanks! Your final order is: {full_order}. The total price is ${total_price:.2f}. Have a great day!")
    
    session['confirmed_order'] = full_order

    # Return JSON response including the confirmed order
    return jsonify({
        'audioUrl': audio_url,
        'message': "Order confirmed",
        'orderConfirmed': True,
        'confirmedOrder': session.get('confirmed_order', '')
    })  
    
def speak_text(message):
    audio_dir = 'static/audio'
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)

    filename = f"message_{int(time.time())}.mp3"
    file_path = os.path.join(audio_dir, filename)
    tts = gTTS(text=message, lang='en')
    tts.save(file_path)

    # Play the message if needed
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()
    os.remove(file_path)

    return url_for('static', filename=f'audio/{filename}')

def recognize_speech(recognizer, source):
    
    if not isinstance(recognizer, sr.Recognizer):
        raise TypeError("`recognizer` must be `Recognizer` instance")

    if not isinstance(source, sr.Microphone):
        raise TypeError("`source` must be `Microphone` instance")

    recognizer.adjust_for_ambient_noise(source)
    print("I'm listening, please speak...")
    audio = recognizer.listen(source)

    try:
        return recognizer.recognize_google(audio)
    except sr.RequestError:
        return "API unavailable"
    except sr.UnknownValueError:
        return "Unable to recognize speech"


import spacy

nlp = spacy.load("en_core_web_sm")

def parse_order_nlp(order):
    doc = nlp(order)

    order_components = {
        "items": [],
        "sizes": [],
        "milks": [],
        "syrups": [],
        "toppings": [],
        "extra_shots": []
    }

    current_quantity = 1  
    skip_next = False 

    for i, token in enumerate(doc):
        if skip_next:
            skip_next = False
            continue

        # print(f"Processing token: {token.text}")
        text_lower = token.text.lower()

        if token.text.isdigit():
            current_quantity = int(token.text)

        else:
            potential_item = text_lower
            if i + 1 < len(doc):
                next_word = doc[i + 1].text.lower()
                combined_item = f"{text_lower} {next_word}"
                if combined_item in [item.lower() for item in menu_items]:
                    potential_item = combined_item
                    skip_next = True

            if potential_item in [item.lower() for item in menu_items]:
                order_components['items'].append((current_quantity, potential_item.capitalize()))
                current_quantity = 1 
            elif text_lower in [size.lower() for size in cup_sizes]:
                order_components['sizes'].append(token.text.capitalize())
            elif text_lower in [milk.lower() for milk in milk_types]:
                order_components['milks'].append(token.text.capitalize())
            elif text_lower in [syrup.lower() for syrup in syrups]:
                order_components['syrups'].append(token.text.capitalize())
            elif text_lower in [topping.lower() for topping in toppings]:
                order_components['toppings'].append(token.text.capitalize())
            elif token.text in extra_shots:
                order_components['extra_shots'].append(token.text)

        print(f"Current order components: {order_components}")

    return order_components



@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return 'No audio file', 400

    audio_file = request.files['audio']
    recognizer = sr.Recognizer()
    audio_data = sr.AudioFile(audio_file)

    with audio_data as source:
        audio = recognizer.record(source)
    
    try:
        text = recognizer.recognize_google(audio)
        return text
    except sr.RequestError:
        return "API unavailable", 500
    except sr.UnknownValueError:
        return "Unable to recognize speech", 400

@app.route('/checkout')
def checkout():
    order = session.get('confirmed_order', 'No order found')
    price = session.get('total_price', 0.0)
    return render_template('checkout.html', order=order, price=price)




if __name__ == '__main__':
    app.run(debug=True)
