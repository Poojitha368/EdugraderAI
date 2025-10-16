import requests
import json

url = "http://localhost:11434/api/chat"

def FindLLMResponse(prompt):
    payload = {
        "model": "llama2",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }

    full_response = ""

    with requests.post(url, json=payload, stream=True) as response:
        for line in response.iter_lines():
            if line:  
                data = json.loads(line.decode("utf-8"))
                if "message" in data and "content" in data["message"]:
                    full_response += data["message"]["content"]
                if data.get("done"):
                    break

    return full_response