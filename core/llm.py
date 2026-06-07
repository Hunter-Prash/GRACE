import asyncio
from google import genai
from google.genai import errors
from core.config import MY_GEMINI_KEY

session_input_tokens = 0
session_output_tokens = 0

def init_llm_client():
    if not MY_GEMINI_KEY:
        print("WARNING: Gemini API Key not found!")
        return None
    return genai.Client(api_key=MY_GEMINI_KEY)

async def send_message_with_retry(chat_session, user_cmd, hud, max_retries=3):
    delay = 2.0
    for attempt in range(max_retries):
        try:
            response = chat_session.send_message(user_cmd)
            return response
        except errors.ClientError as e:
            code = getattr(e, 'code', None)
            if code == 429 and attempt < max_retries - 1:
                hud.add_message("GRACE", f"Rate limit hit. Retrying in {int(delay)}s...")
                await asyncio.sleep(delay)
                delay *= 2
            else:
                raise e
