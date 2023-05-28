ChatClaude - A slack bot that interfaces Claude with OpenAI-like chat completion API

# READ FIRST
This project is for learning and researching integration with Claude before Claude API is publicly available. You are NOT ALLOWED to host this project as a service or in anyway exploit the Claude service and I take no responsibility. Please be considerate of the fact that we can access Claude for free with Slack is a privilege.

# Differences between this API and OpenAI Chat Completion API
1. **DO NOT** send chat history in the request. Claude automatically treats messages in one Slack thread as one context window. You only need to send the newest user message in request. 
2. `id` in response body is the Slack identifier of a thread (aka. `thread_ts`).
3. You can pass `thread_ts` in request body if you want to reply to existing thread (aka. continuing a chat), otherwise a new thread will be created.
4. `reply` (stream: true) in response body is the corresponding reply message identifier (Claude sometimes reply more than once, and those messages are streamed to you together as they appear, e.g. you might recieve delta from the first reply message after receivng delta from the second reply message)
5. `replies` (streams: false) in response body is the collection of all reply message identifiers responding to your user message (Claude sometimes reply more than once, and replies are joined as one content string)

# Usage
> Please refer to Slack Bolt getting started document: https://slack.dev/bolt-python/tutorial/getting-started#create-an-app
1. Create a Slack App
2. In `Settings > Socket Mode` tab:
    1. Turn `Socket Mode` on
3. In `Features > OAuth & Permissions` tab:
    1. Add the following Bot scopes: `channels:history`, `channels:read`, `chat:write`, `users:read`
    2. Add the following User scopes (Claude does not respond to message sent from bot, so messages will be sent on your behalf): `channels:history`, `channels:read`, `chat:write`, `users:read`
    3. Install App to your workspace
    4. Save Bot token
    5. Save User token
    6. Save App token
4. In `Features > Event Subscriptions` tab:
    1. Turn `Enable Events` on
    2. In `Subscribe to bot events`, add `message.channels`
5. Invite your bot to the channel you want it to interact with Claude
6. Run bot server locally (Make sure to adjust how you enable venv based on your OS)
```
python -m venv venv
source ./venv/bin/activate
pip install -r requirement.txt
export "SLACK_BOT_TOKEN" = YOUR_SLACK_BOT_TOKEN
export "SLACK_USER_TOKEN" = YOUR_SLACK_USER_TOKEN
export "SLACK_APP_TOKEN" = YOUR_SLACK_APP_TOKEN
export "CLAUDE_CHANNEL" = YOUR_CHANNEL_NAME
uvicorn main:api
```

# Example
## stream: true
POST localhost:8000/v1/chat/completions
```
{
  "model": "claude",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": true,
  "thread_ts": "1685251222.733349"
}
```
Response
```
data: {"id": "1685251222.733349", "reply": "1685252332.025779", "object": "chat.completion.chunk", "created": 1685252332, "model": "claude", "choices": [{"index": 0, "finish_reason": null, "delta": {"content": ""}}]}
data: {"id": "1685251222.733349", "reply": "1685252332.025779", "object": "chat.completion.chunk", "created": 1685252333, "model": "claude", "choices": [{"index": 0, "finish_reason": null, "delta": {"content": " Hello!"}}]}
data: [DONE]
```
## stream: false
POST localhost:8000/v1/chat/completions
```
{
  "model": "claude",
  "messages": [{"role": "user", "content": "Hello"}],
}
```
Response
```
{
    "id": "1685280565.274649",
    "replies": [
        "1685280566.444699"
    ],
    "object": "chat.completion",
    "created": 1685280567,
    "model": "claude",
    "choices": [
        {
            "index": 0,
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": " Hello! My name is Claude."
            }
        }
    ]
}
```
