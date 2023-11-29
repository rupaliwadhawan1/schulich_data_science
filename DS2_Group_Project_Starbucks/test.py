from flask import Flask
from flask import request, jsonify,render_template, url_for, session
import speech_recognition as sr
from gtts import gTTS
import pygame
import os
import time
import pandas as pd

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

app = Flask(__name__)
app.secret_key = 'your_secret_key' 

pygame.mixer.init()

@app.route('/')
def home():
    return render_template('menu.html')

@app.route('/voice_order')
def main():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    speak_message("Welcome to Starbucks, please place your order.")
    print("Spoken the welcome message...")

    order_text = recognize_speech_from_mic(recognizer, microphone)
    print(f"Order captured: {order_text}")

    speak_message(f"You ordered: {order_text}. Is this correct? Please say Yes or No.")
    print("Repeated the order...")

    confirmation = recognize_speech_from_mic(recognizer, microphone)
    print(f"Confirmation captured: {confirmation}")

    if "yes" in confirmation.lower():
         audio_url = speak_message("Thank you, your order has been confirmed.")
    elif "no" in confirmation.lower():
        audio_url = speak_message("Let's try that again. Please place your order.")
    else:
        audio_url = speak_message("Sorry, I didn't catch that. Please try again.")
    order_confirmed = "yes" in confirmation.lower()
    
    if "yes" in confirmation.lower():
        session['confirmed_order'] = order_text 
    
    return jsonify({
        'audioUrl': audio_url, 
        'message': "Order Confirmed", 
        'orderConfirmed': order_confirmed,  # Use the boolean variable here
        'confirmedOrder': order_text if order_confirmed else ""})
        
        
def speak_message(message):
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

def recognize_speech_from_mic(recognizer, microphone):
    
    if not isinstance(recognizer, sr.Recognizer):
        raise TypeError("`recognizer` must be `Recognizer` instance")

    if not isinstance(microphone, sr.Microphone):
        raise TypeError("`microphone` must be `Microphone` instance")

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("I'm listening, please speak...")
        audio = recognizer.listen(source)

    try:
        return recognizer.recognize_google(audio)
    except sr.RequestError:
        return "API unavailable"
    except sr.UnknownValueError:
        return "Unable to recognize speech"
    

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
    confirmed_order = session.get('confirmed_order', {})
    if not confirmed_order:
        return "No order found", 400

    print("Confirmed order:", confirmed_order)  # Debugging line

    # Additional debugging to inspect the 'items'
    if 'items' in confirmed_order:
        print("Items in confirmed order:", confirmed_order['items'])
    
    order_summary = construct_order_summary(confirmed_order)
    item_price = calculate_price(confirmed_order)

    return render_template('checkout.html', order_summary=order_summary, price=item_price)

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

if __name__ == '__main__':
    app.run(debug=True)


