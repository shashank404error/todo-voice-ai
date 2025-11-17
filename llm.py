import google.generativeai as genai
from setting import settings
import json
import re

def strip_markdown_code_block(text: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)

def generate_llm_response(transcribed_text: str, all_task: dict) -> dict:
    genai.configure(api_key=settings.GEMINI_API_KEY)

    model = genai.GenerativeModel("gemini-2.5-flash-lite")

    prompt = fetch_default_prompt(transcribed_text,all_task)

    # Stream the response from Gemini
    response_text = ""
    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            response_text += chunk.text
    except Exception as e:
        raise RuntimeError(f"Error during content generation: {e}")

    # Try to parse the response as JSON
    try:
        cleaned_text = strip_markdown_code_block(response_text)
        json_response = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from model response: {e}\nRaw response: {response_text}")

    return json_response


def fetch_default_prompt(user_command: str, all_task: dict) -> str:
    """
    prompt for llm to form task from user command.
    
    Args:
        user_command (str): The text transcribed from speech
        
    Returns:
        str: The structured JSON to perform action on task object
    """
    return f"""You are an assistant that translates natural-language user commands into structured JSON instructions for a Todo application.

Your ONLY task is to understand the user'’'s intent and return a JSON object that the system can execute.

The Todo app supports the following actions:
1. "create"      → create a new task
2. "fetch"       → fetch task details
3. "delete"      → delete a task
4. "schedule"    → schedule/update a task's time
5. "none"        → if the user command does not map to any of the above

You are also given a list named **all_task**, which contains existing tasks with:
- index
- title
- description
- scheduled_time (RFC3339)

You MUST use this list to identify which tasks the user is referring to.

The JSON MUST follow this exact schema:

```{{
  "action": "create" | "fetch" | "delete" | "schedule" | "none",
  "message": "short human-readable explanation",
  "task": {{
    "index": number or null,
    "matched_indexes": [array of numbers],
    "title": string,
    "description": string,
    "scheduled_time": "RFC3339 timestamp" or ""
  }}
}}```

Rules:
- Always return **valid JSON only**. No commentary, no surrounding text.
- Do NOT wrap JSON in markdown.
- Never hallucinate missing details. Use "" or null where appropriate.

- ACTION LOGIC:

  • CREATE:
      - Ignore all_task.
      - Extract the clearest title, optional description, and time.
      - Set "index": null and "matched_indexes": [].

  • DELETE:
      - Identify ALL matching tasks in all_task.
      - "matched_indexes" MUST include all matches.
      - "index" MUST contain the single best match index (even if multiple match).

  • FETCH:
      - Identify ALL matching tasks in all_task.
      - "matched_indexes" MUST include all matches.
      - "index" MUST contain the single best match index.

  • SCHEDULE:
      - Identify the SINGLE BEST MATCHING task in all_task.
      - That becomes "index".
      - "matched_indexes" MUST contain exactly that same one index.
      - Convert any time reference into RFC3339 if possible especially for schedule action.

  • NONE:
      - If user intent is unclear or unsupported.

- Matching logic:
    • Use semantic similarity between the user command and task titles/descriptions.
    • “meeting with my manager” → matches tasks whose title mentions “manager”.
    • “cancel meeting with colleague” → matches “Meeting with colleague”.
    • “schedule meeting with Sayak tomorrow 5pm” → matches relevant item.

Return EXACTLY one JSON object.

Now convert the following user command and the given all_task list into the JSON format described above:

User command:
{user_command}

Existing tasks (all_task):
{all_task}

"""