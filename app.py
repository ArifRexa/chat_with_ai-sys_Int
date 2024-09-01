import time
import logging
import flask
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
import threading
from services import AIService

app = Flask(__name__)
app.config['DEBUG'] = True

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_service = AIService()


@app.route('/')
def index():
    return render_template('index.html')


# @app.route('/tts')
# def combined():
#     return render_template('process_audio_chat.html')


# @app.route('/transcribe', methods=['POST'])
# def handle_transcription():
#     if 'file' not in request.files:
#         return jsonify({"error": "No file part"}), 400
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({"error": "No selected file"}), 400
#     if file:
#         audio_data = file.read()
#         transcribed_text = ai_service.transcribe_voice(audio_data)
#         detected_language = ai_service.detect_language(transcribed_text)
#         print(f"Transcribed Text: {transcribed_text}")
#         print(f"Detected Language: {detected_language}")
#         return jsonify({"Transcribed Text": transcribed_text, "Detected Language": detected_language})

@app.route('/transcribe', methods=['POST'])
def handle_transcription():
    if 'file' not in request.files:
        logger.error("No file part in the request")
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        logger.error("No file selected for uploading")
        return jsonify({"error": "No selected file"}), 400
    if file:
        audio_data = file.read()
        transcribed_text = ai_service.transcribe_voice(audio_data)
        logger.info(transcribed_text)
        logger.info("Transcription successful")
        return jsonify({"Transcribed Text": transcribed_text})


@app.route('/translate', methods=['POST'])
def translate_text():
    content = request.json
    text = content.get('text')
    src_lang = content.get('source_lang')
    print("source lng: ", src_lang)
    tgt_lang = content.get('target_lang')
    print("target lang: ", tgt_lang)
    logger.info(f"Source Language: {src_lang}, Target Language: {tgt_lang}")

    intermediate_lang = "sme"
    if (src_lang == "nor" and tgt_lang == "eng") or (src_lang == "eng" and tgt_lang == "nor"):
        first_translation = ai_service.perform_translation(text, src_lang, tgt_lang)
        if 'error' in first_translation:
            logger.error(f"Translation error: {first_translation}")
            return jsonify(first_translation), 400

        second_translation = ai_service.perform_translation(first_translation['Translated Text'], intermediate_lang,
                                                            tgt_lang)
        if 'error' in second_translation:
            logger.error(f"Second translation error: {second_translation}")
            return jsonify(second_translation), 400

        return jsonify({"Translated Text": second_translation['Translated Text']})
    else:
        result = ai_service.perform_translation(text, src_lang, tgt_lang)
        if 'error' in result:
            logger.error(f"Translation error: {result}")
            return jsonify(result), 400
        return jsonify({"Translated Text": result['Translated Text']})


@app.route('/chat', methods=['POST'])
def chat_with_openai_route():
    content = request.json
    transcribed_text = content.get('text')
    if not transcribed_text:
        logger.error("No text provided for chat")
        return jsonify({'error': 'No text provided'}), 400

    chat_response = ai_service.chat_with_openai(transcribed_text)
    print(f"ChatGPT Response: {chat_response}")
    logger.info(f"ChatGPT Response: {chat_response}")

    return jsonify({"ChatGPT Response": chat_response})


@app.route('/tts', methods=['POST'])
def tts_route():
    data = request.json
    text = data.get('text')
    if not text:
        logger.error("No text provided for TTS")
        return jsonify({'error': 'No text provided'}), 400

    filename = f'Generated_Audio_{time.time()}.mp3'
    threading.Thread(target=ai_service.tts, args=(text, filename)).start()
    logger.info("TTS processing started")
    return jsonify({'message': 'TTS processing started, please wait...', 'filename': filename})


# @app.route('/process_audio_chat', methods=['GET', 'POST'])
# def process_audio_chat():
#     if request.method == 'POST':
#         if 'file' not in request.files:
#             logger.error("No file part in the request")
#             return jsonify({"error": "No file part"}), 400
#         file = request.files['file']
#         if file.filename == '':
#             logger.error("No file selected for uploading")
#             return jsonify({"error": "No selected file"}), 400
#         if file:
#
#             audio_data = file.read()
#
#             target_lang = request.form.get('lang', 'sme')  # Get target language from form, default to
#             print(target_lang, "target lang")
#             filename = f'Generated_Audio_{target_lang}_{time.time()}.mp3'
#             message = ai_service.process_audio_in_thread(audio_data, target_lang, filename)
#             logger.info(f"Audio processing started for target language {target_lang}")
#             return jsonify(message)
#         logger.error("No file part in the request")
#         return jsonify({"error": "No file part"}), 400
#
#     else:
#         return render_template('process_audio_chat.html')
# @app.route('/process_audio_chat', methods=['GET', 'POST'])
# def process_audio():
#     if request.method == 'POST':
#         if 'file' not in request.files:
#             logger.error("No file part in the request")
#             return jsonify({"error": "No file part"}), 400
#         file = request.files['file']
#         if file.filename == '':
#             logger.error("No file selected for uploading")
#             return jsonify({"error": "No selected file"}), 400
#         if file:
#             audio_data = file.read()
#             target_lang = request.form.get('lang', 'sme')
#             chatgpt_prompt = request.form.get('prompt', None)
#             filename = f'Generated_Audio_{target_lang}_{time.time()}.mp3'
#             # logger.info(f'{target_lang}, {chatgpt_prompt}, {type(chatgpt_prompt)}')
#             result = ai_service.process_audio(audio_data, filename, chatgpt_prompt)
#             return jsonify(result)
#         return jsonify({"error": "No file part"}), 400
#     else:
#         return render_template('process_audio_chat.html')
@app.route('/process_audio_chat', methods=['GET', 'POST'])
def process_audio():
    if request.method == 'POST':
        if 'file' not in request.files:
            logger.error("No file part in the request")
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']
        if file.filename == '':
            logger.error("No file selected for uploading")
            return jsonify({"error": "No selected file"}), 400
        logger.info(file.filename)
        if file:
            if file.filename.lower().endswith(('.mp3', '.wav')):
                # Audio file processing
                audio_data = file.read()
                target_lang = request.form.get('lang', 'sme')
                chatgpt_prompt = request.form.get('prompt', None)
                filename = f'Generated_Audio_{target_lang}_{time.time()}.mp3'
                result = ai_service.process_audio(audio_data, filename, chatgpt_prompt)
                return jsonify(result)

            elif file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Image file processing
                image_data = file.read()
                target_lang = request.form.get('lang', 'sme')
                chatgpt_prompt = request.form.get('prompt', None)
                filename = f'Generated_Image_{target_lang}_{time.time()}.jpg'  # Adjust filename as needed
                result = ai_service.process_audio(image_data, filename,
                                                  chatgpt_prompt)  # Note: 'process_audio' is used for both audio and image here
                logger.info(chatgpt_prompt)
                logger.info(result)
                return jsonify(result)

            else:
                return jsonify({"error": "Unsupported file format"}), 400

        return jsonify({"error": "No file part"}), 400

    else:
        return render_template('process_audio_chat.html')


@app.route('/audio/<filename>')
def get_audio(filename):
    return send_from_directory('static/audio', filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=True)
