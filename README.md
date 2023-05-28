ChatClaude - A slack bot that interfaces Claude with OpenAI-like chat completion API

# READ FIRST
This project is for learning and researching integration with Claude before Claude API is publicly available. You are NOT ALLOWED to host this project as a service or in anyway exploit the Claude service and I take no responsibility. Please be considerate of the fact that we can access Claude for free with Slack is a privilege.

# Different between this API and OpenAI Chat Completion API
1. DO NOT send chat history in the request. Each thread is a context window, every message in the thread is automatically handled by Claude as chat histoy. You only need to send the newest user message in request. 
2. `id` in response is the `thread_ts` of the Slack thread.
3. Pass `thread_ts` in request body if you want to reply to existing thread (aka. continuing a chat)
4. `reply` (stream: true) is the corresponding reply message ts (Claude sometimes reply more than once, and those messages are streamed to you together as they appear)
5. `replies` (streams: false) is the collection of all reply message ts responding to your user message (Claude sometimes reply more than once, and replies are joined in the response)

# Run locally (Make sure to adjust how you enable venv based on your OS)
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
