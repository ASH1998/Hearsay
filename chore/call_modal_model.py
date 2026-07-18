import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url=os.environ.get("MODAL_PROXY_URL"),
    api_key="unused",
    default_headers={
        "Modal-Key": os.environ["MODAL_PROXY_TOKEN_ID"],
        "Modal-Secret": os.environ["MODAL_PROXY_TOKEN_SECRET"],
    },
)

completion = client.chat.completions.create(
    model="thinkingmachines/Inkling-NVFP4",
    messages=[
        {
            "role": "system",
            "content": "You are a concise technical assistant.",
        },
        {
            "role": "user",
            "content": "Extract the name, age, and city: Ada, 36, London.",
        },
    ],
    temperature=0.3,
    max_tokens=2048,
    top_p=0.9,
    stream=False,
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person_info",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "city": {"type": "string"},
                },
                "required": ["name", "age", "city"],
                "additionalProperties": False,
            },
        },
    },
    tools=[
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        },
    ],
    tool_choice="auto",
    extra_body={"reasoning_effort": "high"},
    extra_headers={
        "Modal-Session-ID": "session_12345", # this is for tracking purposes, you can set it to any string
    },
)
print(completion.choices[0].message.content)