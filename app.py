import hashlib
from flask import Flask, request, jsonify, Response
import requests
import io
import json
import re
import uuid
import random
import time
from functools import wraps

app = Flask(__name__)

TARGET_URL = "https://grok.com/rest/app-chat/conversations/new"
CHECK_URL = "https://grok.com/rest/rate-limits"
MODELS = ["grok-2", "grok-3", "grok-3-thinking"]
CONFIG = {}
TEMPORARY_MODE = False
COOKIE_NUM = 0
COOKIE_LIST = []
LAST_COOKIE_INDEX = {}
PASSWORD = ""

USER_AGENTS = [
    # Windows - Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Windows - Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    # Windows - Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81",
    # Windows - Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
    # macOS - Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # macOS - Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0.1 Safari/605.1.15",
    # macOS - Firefox
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:132.0) Gecko/20100101 Firefox/132.0",
    # macOS - Opera
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Linux - Chrome
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Linux - Firefox
    "Mozilla/5.0 (X11; Linux i686; rv:124.0) Gecko/20100101 Firefox/124.0",
]


def resolve_config():
    global COOKIE_NUM, COOKIE_LIST, LAST_COOKIE_INDEX, TEMPORARY_MODE, CONFIG, PASSWORD
    with open("config.json", "r") as f:
        CONFIG = json.load(f)
    for cookies in CONFIG["cookies"]:
        session = requests.Session()
        session.headers.update(
            {"user-agent": random.choice(USER_AGENTS), "cookie": cookies}
        )

        COOKIE_LIST.append(session)
    COOKIE_NUM = len(COOKIE_LIST)
    TEMPORARY_MODE = CONFIG["temporary_mode"]
    for model in MODELS:
        LAST_COOKIE_INDEX[model] = CONFIG["last_cookie_index"][model]
    PASSWORD = CONFIG.get("password", "")


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not PASSWORD:
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or not check_auth(auth.token):
            return jsonify({"error": "Unauthorized access"}), 401
        return f(*args, **kwargs)

    return decorated


def check_auth(password):
    return hashlib.sha256(password.encode()).hexdigest() == PASSWORD


@app.route("/v1/models", methods=["GET"])
@require_auth
def get_models():
    model_list = []
    for model in MODELS:
        model_list.append(
            {
                "id": model,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "Elbert",
                "name": model,
            }
        )
    return jsonify({"object": "list", "data": model_list})


@app.route("/v1/chat/completions", methods=["POST"])
@require_auth
def chat_completions():
    print("Received request")
    openai_request = request.get_json()
    print(openai_request)
    stream = openai_request.get("stream", False)
    messages = openai_request.get("messages")
    model = openai_request.get("model")
    if model not in MODELS:
        return jsonify({"error": "Model not available"}), 500
    if messages is None:
        return jsonify({"error": "Messages is required"}), 400
    disable_search, force_concise, messages = magic(messages)
    message = format_message(messages)
    is_reasoning = len(model) > 6
    model = model[0:6]
    return (
        send_message(message, model, disable_search, force_concise, is_reasoning)
        if stream
        else send_message_non_stream(
            message, model, disable_search, force_concise, is_reasoning
        )
    )


def get_next_account(model):
    current = (LAST_COOKIE_INDEX[model] + 1) % COOKIE_NUM
    LAST_COOKIE_INDEX[model] = current
    print(f"Using account {current+1}/{COOKIE_NUM} for {model}")
    CONFIG["last_cookie_index"][model] = current
    with open("config.json", "w") as f:
        json.dump(CONFIG, f, indent=4)
    return COOKIE_LIST[current]


def send_message(message, model, disable_search, force_concise, is_reasoning):
    headers = {
        "authority": "grok.com",
        "method": "POST",
        "path": "/rest/app-chat/conversations/new",
        "scheme": "https",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "origin": "https://grok.com",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://grok.com/",
        "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    payload = {
        "temporary": TEMPORARY_MODE,
        "modelName": "grok-3",
        "message": message,
        "fileAttachments": [],
        "imageAttachments": [],
        "disableSearch": disable_search,
        "enableImageGeneration": False,
        "returnImageBytes": False,
        "returnRawGrokInXaiRequest": False,
        "enableImageStreaming": True,
        "imageGenerationCount": 2,
        "forceConcise": force_concise,
        "toolOverrides": {},
        "enableSideBySide": True,
        "isPreset": False,
        "sendFinalMetadata": True,
        "customInstructions": "",
        "deepsearchPreset": "",
        "isReasoning": is_reasoning,
    }
    session = get_next_account(model)
    try:
        response = session.post(TARGET_URL, headers=headers, json=payload, stream=True)
        response.raise_for_status()

        def generate():
            try:
                print("---------- Response ----------")
                cnt = 2
                thinking = 2
                for line in response.iter_lines():
                    if line:
                        if cnt != 0:
                            cnt -= 1
                        else:
                            decoded_line = line.decode("utf-8")
                            data = json.loads(decoded_line)
                            token = data["result"]["response"]["token"]
                            content = ""
                            if is_reasoning:
                                if thinking == 2:
                                    thinking = 1
                                    content = f"<Thinking>\n{token}"
                                    print(f"{content}", end="")
                                elif thinking & (
                                    not data["result"]["response"]["isThinking"]
                                ):
                                    thinking = 0
                                    content = f"\n</Thinking>\n{token}"
                                    print(f"{content}", end="")
                                else:
                                    content = token
                                    print(content, end="")
                            else:
                                content = token
                                print(content, end="")
                            openai_chunk = {
                                "id": "chatcmpl-" + str(uuid.uuid4()),
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {"content": content},
                                        "finish_reason": None,
                                    }
                                ],
                            }
                            yield f"data: {json.dumps(openai_chunk)}\n\n"
                            if data["result"]["response"]["isSoftStop"]:
                                openai_chunk = {
                                    "id": "chatcmpl-" + str(uuid.uuid4()),
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": model,
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {"content": content},
                                            "finish_reason": "completed",
                                        }
                                    ],
                                }
                                yield f"data: {json.dumps(openai_chunk)}\n\n"
                                break
                print("\n---------- Response End ----------")
                yield f"data: [DONE]\n\n"
            except Exception as e:
                print(f"Failed to send message: {e}")
                yield f'data: {{"error": "{e}", "status": {response.status_code}}}\n\n'

        return Response(generate(), content_type="text/event-stream")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message: {e}")
        return jsonify({"error": f"{e}", "status": response.status_code})


def send_message_non_stream(
    message, model, disable_search, force_concise, is_reasoning
):
    headers = {
        "authority": "grok.com",
        "method": "POST",
        "path": "/rest/app-chat/conversations/new",
        "scheme": "https",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "origin": "https://grok.com",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://grok.com/",
        "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    payload = {
        "temporary": TEMPORARY_MODE,
        "modelName": "grok-3",
        "message": message,
        "fileAttachments": [],
        "imageAttachments": [],
        "disableSearch": disable_search,
        "enableImageGeneration": False,
        "returnImageBytes": False,
        "returnRawGrokInXaiRequest": False,
        "enableImageStreaming": True,
        "imageGenerationCount": 2,
        "forceConcise": force_concise,
        "toolOverrides": {},
        "enableSideBySide": True,
        "isPreset": False,
        "sendFinalMetadata": True,
        "customInstructions": "",
        "deepsearchPreset": "",
        "isReasoning": is_reasoning,
    }
    session = get_next_account(model)
    thinking = 2
    try:
        response = session.post(TARGET_URL, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        cnt = 2
        try:
            print("---------- Response ----------")
            buffer = io.StringIO()
            for line in response.iter_lines():
                if line:
                    if cnt != 0:
                        cnt -= 1
                    else:
                        decoded_line = line.decode("utf-8")
                        data = json.loads(decoded_line)
                        token = data["result"]["response"]["token"]
                        content = ""
                        if is_reasoning:
                            if thinking == 2:
                                thinking = 1
                                content = f"<Thinking>\n{token}"
                                print(f"{content}", end="")
                                buffer.write(content)
                            elif thinking & (
                                not data["result"]["response"]["isThinking"]
                            ):
                                thinking = 0
                                content = f"\n</Thinking>\n{token}"
                                print(f"{content}", end="")
                                buffer.write(content)
                            else:
                                content = token
                                print(content, end="")
                                buffer.write(content)
                        else:
                            content = token
                            print(content, end="")
                            buffer.write(content)
                        if data["result"]["response"]["isSoftStop"]:
                            break
            print("\n---------- Response End ----------")
            openai_response = {
                "id": "chatcmpl-" + str(uuid.uuid4()),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": buffer.getvalue()},
                        "finish_reason": "completed",
                    }
                ],
            }
            return jsonify(openai_response)
        except Exception as e:
            print(f"Failed to send message: {e}")
            return jsonify({"error": f"{e}", "status": response.status_code})
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message: {e}")
        return jsonify({"error": f"{e}", "status": response.status_code})


def format_message(messages):
    buffer = io.StringIO()
    role_map, prefix, messages = extract_role(messages)
    for message in messages:
        role = message.get("role")
        role = "\b" + role_map[role] if prefix else role_map[role]
        content = message.get("content").replace("\\n", "\n")
        pattern = re.compile(r"<\|removeRole\|>\n")
        if pattern.match(content):
            content = pattern.sub("", content)
            buffer.write(f"{content}\n")
        else:
            buffer.write(f"{role}: {content}\n\n")
    formatted_message = buffer.getvalue()
    with open("message_log.txt", "w", encoding="utf-8") as f:
        f.write(formatted_message)
    return formatted_message


def extract_role(messages):
    role_map = {"user": "Human", "assistant": "Assistant", "system": "System"}
    prefix = False
    first_message = messages[0]["content"]
    pattern = re.compile(
        r"""
        <roleInfo>\s*
        user:\s*(?P<user>[^\n]*)\s*
        assistant:\s*(?P<assistant>[^\n]*)\s*
        system:\s*(?P<system>[^\n]*)\s*
        prefix:\s*(?P<prefix>[^\n]*)\s*
        </roleInfo>\n
    """,
        re.VERBOSE,
    )
    match = pattern.search(first_message)
    if match:
        role_map = {
            "user": match.group("user"),
            "assistant": match.group("assistant"),
            "system": match.group("system"),
        }
        prefix = match.group("prefix") == "1"
        messages[0]["content"] = pattern.sub("", first_message)
        print(f"Extracted role map:")
        print(
            f"User: {role_map['user']}, Assistant: {role_map['assistant']}, System: {role_map['system']}"
        )
        print(f"Using prefix: {prefix}")
    return (role_map, prefix, messages)


def magic(messages):
    first_message = messages[0]["content"]
    disable_search = False
    if re.search(r"<\|disableSearch\|>", first_message):
        disable_search = True
        print("Disable search")
        first_message = re.sub(r"<\|disableSearch\|>", "", first_message)
    force_concise = False
    if re.search(r"<\|forceConcise\|>", first_message):
        force_concise = True
        print("Force concise")
        first_message = re.sub(r"<\|forceConcise\|>", "", first_message)
    messages[0]["content"] = first_message
    return (disable_search, force_concise, messages)


def check_rate_limit(session, model, is_reasoning):
    headers = {
        "authority": "grok.com",
        "method": "POST",
        "path": "/rest/rate-limits",
        "scheme": "https",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "origin": "https://grok.com",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://grok.com/",
        "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    payload = {
        "requestKind": "REASONING" if is_reasoning else "DEFAULT",
        "modelName": model,
    }
    try:
        response = session.post(CHECK_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = json.loads(response.content)
        if data["remainingQueries"] != 0:
            return (True, data["remainingQueries"])
        else:
            available_time = time.time() + data["waitTimeSeconds"]
            return (False, available_time)

    except Exception as e:
        print(f"Failed to check rate limit: {e}")
        return (False, None)


resolve_config()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9898)
