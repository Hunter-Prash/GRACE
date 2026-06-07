import time
from core.config import db_table

def load_chat_history_from_ddb(session_id="default"):
    """Loads chat history from DynamoDB and returns it in standard SDK dictionary format."""
    if db_table is None:
        return []
    try:
        response = db_table.get_item(Key={'SessionId': session_id})
        item = response.get('Item')
        if not item or 'History' not in item:
            return []
        history = []
        for msg in item['History']:
            role = msg.get('role')
            text = msg.get('text', '')
            history.append({
                "role": role,
                "parts": [{"text": text}]
            })
        return history
    except Exception as e:
        print(f"Error loading chat history from DynamoDB: {e}")
        return []

def save_chat_messages_to_ddb(session_id, user_msg, model_response):
    """Saves user query and model response to DynamoDB, keeping a rolling window of the last 30 messages."""
    if db_table is None:
        return
    try:
        response = db_table.get_item(Key={'SessionId': session_id})
        item = response.get('Item')
        history = item.get('History', []) if item else []
        
        history.append({"role": "user", "text": user_msg})
        history.append({"role": "model", "text": model_response})
        
        # Keep rolling window of last 30 messages
        if len(history) > 30:
            history = history[-30:]
            
        db_table.put_item(
            Item={
                'SessionId': session_id,
                'History': history,
                'LastUpdated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        )
    except Exception as e:
        print(f"Error saving chat history to DynamoDB: {e}")
