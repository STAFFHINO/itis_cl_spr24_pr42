"""Telegram Bot on Yandex Cloud Function."""
import io
import json
import os
import requests


def get_temperature(place: str, token: str) -> str:

    url = "https://api.openweathermap.org/data/2.5/weather"
    parameters = {"q": place, "appid": token, "lang": "ru", "units": "metric"}
    response = requests.get(url=url, params=parameters).json()
    temperature = response["main"]["temp"]

    return temperature


def send_message(text: str, chat_id: str, message_id: str, token: str):

    reply_parameters = {"message_id": message_id}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    parameters = {"chat_id": chat_id, "text": text,
                  "reply_parameters": reply_parameters}
    requests.post(url=url, json=parameters)


def send_voice(voice: bytes, chat_id: str, message_id: str, token: str):
    voice_file = io.BytesIO(voice)

    url = f"https://api.telegram.org/bot{token}/sendVoice"
    parameters = {"chat_id": chat_id}

    requests.post(url=url, data=parameters, files={"voice": voice_file})


def download_file(file_id: str, token: str) -> bytes:
    url = f"https://api.telegram.org/bot{token}/getFile"
    parameters = {"file_id": file_id}

    response = requests.post(url=url, json=parameters).json()

    file = response["result"]
    file_path = file["file_path"]
    download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

    download_response = requests.get(url=download_url)

    file_content = download_response.content

    return file_content


def stt(voice: bytes, token: str) -> str:
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    auth = {"Authorization": f"Bearer {token}"}

    response = requests.post(url=url, headers=auth, data=voice).json()

    text = response["result"]

    return text


def tts(text: str, token: str) -> bytes:
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    params = {"text": text, "voice": "ermil", "emotion": "good"}
    auth = {"Authorization": f"Bearer {token}"}

    yc_tts_response = requests.post(url=url, data=params, headers=auth)

    voice = yc_tts_response.content

    return voice


def handler(event, context):
    yc_function_response = {'statusCode': 200, 'body': ''}
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    ow_token = os.environ.get("WEATHER_TOKEN")
    yc_token = context.token["access_token"]

    update = json.loads(event['body'])

    message = update['message']

    message_id = message["message_id"]
    chat_id = message["chat"]["id"]

    if "text" in message:
        place = message["text"]
        temperature = get_temperature(place=place, token=ow_token)
        send_message(text=temperature, chat_id=chat_id, message_id=message_id,
                     token=tg_token)
        return yc_function_response

    if "voice" in message:
        voice = message["voice"]

        if voice["duration"] > 30:
            error_text = "Голосовое сообщение должно быть короче 30 секунд"
            send_message(text=error_text, chat_id=chat_id,
                         message_id=message_id, token=tg_token)
            return yc_function_response

        voice_content = download_file(file_id=voice["file_id"], token=tg_token)

        place = stt(voice=voice_content, token=yc_token)
        temperature = get_temperature(place=place, token=ow_token)
        yc_tts_voice = tts(text=temperature, token=yc_token)
        send_voice(voice=yc_tts_voice, message_id=message_id, chat_id=chat_id,
                   token=tg_token)

        return yc_function_response

    error_text = "Могу ответить только на текстовое или голосовое сообщение"
    send_message(text=error_text, chat_id=chat_id, message_id=message_id,
                 token=tg_token)
    return yc_function_response