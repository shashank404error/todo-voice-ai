import azure.cognitiveservices.speech as speechsdk
from  llm import generate_llm_response
from util import post_process
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from setting import settings
import todo

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AZURE_SPEECH_KEY = settings.AZURE_SPEECH_KEY
AZURE_SERVICE_REGION = settings.AZURE_SERVICE_REGION

def create_handle_result(websocket: WebSocket, loop: asyncio.AbstractEventLoop, processing_lock: asyncio.Event, task_store: todo.TodoStore):
    def handle_result(evt):
        if evt.result.text:
            text = evt.result.text
            logger.debug(f"Final result received: {text}")

            async def send_result():
                try:
                    processing_lock.clear()

                    remy_response_acknowledged = {
                        "event_type": "ACKNOWLEDGED",
                        "status":"success",
                        "transcribed_text_processed":text
                    }
                    # logger.info(f"remy_response_acknowledged: {remy_response_acknowledged}")
                    await websocket.send_text(json.dumps(remy_response_acknowledged))

                    # fetch all the task in hand
                    all_task = task_store.fetch_all_tasks()
                    ai_resp = generate_llm_response(text,all_task)
                    ai_resp = post_process(ai_resp)
                    # logger.info(f"user_command: [{text}]")
                    # logger.info(f"ai_resp: [{ai_resp}]")

                    selected_task = todo.fetch_task_indexes(ai_resp,task_store)
                    # logger.info(f"selected_task: {selected_task}")

                    todo.handle_action(ai_resp,task_store)

                    all_task = task_store.fetch_all_tasks()
                    # logger.info(f"all_task: {all_task}")
                

                    remy_response_processed = {
                        "event_type": "PROCESSED",
                        "status":"success",
                        "transcribed_text_processed":text,
                        "ai_response":ai_resp,
                        "all_task": all_task,
                        "selected_task": selected_task
                    }
                    logger.info(f"remy_response_processed: {remy_response_processed}")
                    await websocket.send_text(json.dumps(remy_response_processed))
                    logger.info(f"message sent successfully")


                except Exception as e:
                    logger.error(f"Error sending text via WebSocket: {e}")
                finally:
                    processing_lock.set()  # resume audio processing

            try:
                asyncio.run_coroutine_threadsafe(send_result(), loop)
            except Exception as e:
                logger.exception(f"Error scheduling coroutine: {e}")

    return handle_result


@app.websocket("/asr/premium")
async def websocket_endpoint_premium(websocket: WebSocket):
    if AZURE_SPEECH_KEY == "your-speech-key" or AZURE_SERVICE_REGION == "your-region":
        logger.error("Azure Speech credentials not configured")
        await websocket.close(code=1000, reason="Azure Speech credentials not configured")
        return

    await websocket.accept()
    logger.info("WebSocket connection accepted for premium ASR.")

    processing_lock = asyncio.Event()
    processing_lock.set()

    audio_stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SERVICE_REGION)
    speech_config.set_property(
        property_id=speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs,
        value="3000"
    )
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    loop = asyncio.get_event_loop()
    task_store = todo.TodoStore()

    handler = create_handle_result(websocket, loop, processing_lock,task_store)
    speech_recognizer.recognized.connect(handler)

    logger.info("Starting continuous recognition...")
    speech_recognizer.start_continuous_recognition()

    try:
        while True:
            try:
                message = await websocket.receive()
                # print("RAW MESSAGE:", message)
            except Exception as e:
                logger.error(f"WebSocket receive error: {e}")
                break

            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    audio_chunk = message["bytes"]
                    if processing_lock.is_set():
                        audio_stream.write(audio_chunk)
                    else:
                        logger.debug("Audio chunk dropped because backend is processing")
                elif "text" in message:
                    logger.warning(f"Unexpected text message received: {message['text']}")
                    continue
                else:
                    logger.warning(f"Unexpected message format: {message}")
            elif message["type"] == "websocket.disconnect":
                logger.info("WebSocket client disconnected.")
                break
    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket.")
    except Exception as e:
        logger.exception(f"Unexpected error in WebSocket loop: {e}")
    finally:
        speech_recognizer.stop_continuous_recognition()
        audio_stream.close()
        logger.info("Stopped recognition and closed audio stream.")