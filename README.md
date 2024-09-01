# Overview
This Flask application provides several routes for handling transcription, translation, text-to-speech (TTS), and chat with OpenAI's models. The main functionalities include:

1. Transcribing audio files to text using Hugging Face's Whisper model.
2. Translating text between different languages, including a two-step translation involving an intermediate language.
3. Generating responses using OpenAI's GPT models.
4. Converting text to speech and playing the audio using VLC.

## Prerequisites
Ensure you have the following installed:

- Python 3.x
- Flask
- requests
- sounddevice
- scipy
- python-vlc
- openai
- python-dotenv

## Installation

1. Clone the repository.
2. Install the required packages:
   
```bash
pip install flask requests sounddevice scipy python-vlc openai python-dotenv
```



3. Go to the .env file in the root directory and add your API keys.

## Application Structure

- `app.py`: Main application file.
- `templates/index.html`: HTML template for the index route.
- `api.py`: Contains functions for logging in and sending commands to the TTS service.

# Code Explanation

## Imports and Configurations

```python
from flask import Flask, request, jsonify, render_template, send_file
import os
import requests
from openai import OpenAI
from dotenv import load_dotenv
import sounddevice as sd
from scipy.io.wavfile import write
import tempfile
import vlc
import threading
import time
from api import login, send_command
import urllib.parse as urlparse

load_dotenv()
app = Flask(__name__)
app.config['DEBUG'] = True
Initializing OpenAI Client

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
```

## Routes

### Index Route
Renders the `index.html` template.

```python
@app.route('/')
def index():
    return render_template('index.html')
```
### Transcription Route
Handles the transcription of uploaded audio files.

```python
API_URL = "https://api-inference.huggingface.co/models/NbAiLabBeta/nb-whisper-small"
headers = {"Authorization": "Bearer hf_apikeyhere"}

def transcribe_voice(audio_data):
    response = requests.post(API_URL, headers=headers, data=audio_data)
    transcription = response.json()
    return transcription.get('text', 'Transcription failed or "text" key is missing')

@app.route('/transcribe', methods=['POST'])
def handle_transcription():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        audio_data = file.read()
        transcribed_text = transcribe_voice(audio_data)
        return jsonify({"Transcribed Text": transcribed_text})

```
### Translation Route
Translates text using the Tartu NLP API. Handles both direct and intermediate language translations.

```python
@app.route('/translate', methods=['POST'])
def translate_text():
    content = request.json
    text = content.get('text')
    src_lang = content.get('source_lang')
    tgt_lang = content.get('target_lang')

    intermediate_lang = "sme"

    if (src_lang == "nor" and tgt_lang == "eng") or (src_lang == "eng" and tgt_lang == "nor"):
        first_translation = perform_translation(text, src_lang, intermediate_lang)
        if 'error' in first_translation:
            return jsonify(first_translation), 400
        
        second_translation = perform_translation(first_translation['Translated Text'], intermediate_lang, tgt_lang)
        if 'error' in second_translation:
            return jsonify(second_translation), 400
        
        return jsonify({"Translated Text": second_translation['Translated Text']})
    else:
        result = perform_translation(text, src_lang, tgt_lang)
        if 'error' in result:
            return jsonify(result), 400
        return jsonify({"Translated Text": result['Translated Text']})

def perform_translation(text, src_lang, tgt_lang):
    url = "https://api.tartunlp.ai/translation/v2"
    payload = {
        "text": text,
        "src": src_lang,
        "tgt": tgt_lang
    }
    response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
    if response.status_code == 200:
        data = response.json()
        return {"Translated Text": data.get('result', 'No translation found.')}
    else:
        return {"error": "Failed to translate", "message": response.text}

```
### Chat Route
Handles chat interactions with OpenAI's GPT models.

```python
@app.route('/chat', methods=['POST'])
def chat_with_openai():
    content = request.json
    transcribed_text = content.get('text')
    if not transcribed_text:
        return jsonify({'error': 'No text provided'}), 400

    messages = [
        {"role": "system", "content": "You are a very friendly AI assistant."},
        {"role": "user", "content": transcribed_text}
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=256
    )
    return jsonify({"ChatGPT Response": response.choices[0].message.content.strip() if response.choices else "No response generated"})

```

### Text-to-Speech Route
Converts text to speech and plays the audio.

```python
@app.route('/tts', methods=['POST'])
def tts():
    data = request.json
    text = data.get('text')
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    chatgpt_response = text
    threading.Thread(target=menu, args=(chatgpt_response,)).start()
    return jsonify({'message': 'TTS processing started, please wait...'})

def menu(chatgpt_response):
    token = login("tim@valio.no", "8JP9F3ljR4SXc48E")
    if not token:
        print("Login failed")
        return

    text = chatgpt_response
    voice = "Elle22k_CO"
    text_quoted = urlparse.quote(text)
    output = "stream"
    response = send_command(token, voice, text_quoted, output, type="mp3")
    if response.status_code != 200:
        print("Failed to generate speech:", response.text)
        return

    file_path = "./acapela-cloud-stream.mp3"
    with open(file_path, "wb") as file:
        file.write(response.content)
    play_audio(file_path)

def play_audio(file_path):
    player = vlc.MediaPlayer(file_path)
    player.play()
    time.sleep(0.5)
    while player.is_playing():
        time.sleep(0.1)

```

### Process Audio Chat Route
Handles the entire process of receiving an audio file, transcribing it, interacting with ChatGPT, translating the response, and converting it to speech.

```python

@app.route('/process_audio_chat', methods=['POST'])
def process_audio_chat():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    audio_data = file.read()
    try:
        transcribed_text = transcribe_voice(audio_data)
        if not transcribed_text:
            raise ValueError("Transcription failed or no text was returned")
    except Exception as e:
        return jsonify({"error": "Transcription failed", "details": str(e)}), 500

    try:
        chat_response = chat_with_openaiB(transcribed_text)
        if not chat_response:
            raise ValueError("No response generated by ChatGPT")
    except Exception as e:
        return jsonify({"error": "ChatGPT processing failed", "details": str(e)}), 500

    try:
        translated_text = perform_translation(chat_response, 'nor', 'sme')
        if not translated_text:
            raise ValueError("Translation failed or no text was returned")
    except Exception as e:
        return jsonify({"error": "Translation failed", "details": str(e)}), 500

    try:
        audio_file_path = menu(translated_text)
        if not audio_file_path:
            raise ValueError("TTS failed to generate audio file")
        return send_file(audio_file_path, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({"error": "Text-to-Speech conversion failed", "details": str(e)}), 500

```

### Integrated Route
Renders the `process_audio_chat.html` template.

```bash
/process_audio_chat
```


### Running the Application
To run the application, use the following command:

```bash
python app.py
```

If you have docker then can run with this command also
```bash
docker compose up --build -d

docker compose up
```

The application will be accessible at `http://0.0.0.0:5000`.

