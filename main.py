from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
import logging
# logging.basicConfig(level=logging.DEBUG)

import os
import math
import time
import asyncio
from pydantic import BaseModel

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
client = WebClient(token=os.environ["SLACK_USER_TOKEN"])


app = AsyncApp(token=os.getenv("SLACK_BOT_TOKEN"))
handler = AsyncSocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
claudeUserId = ""
claudeChannelId = ""
chatMap: dict = {}
replyMap: dict = {}


@app.event("message")
async def on_message(event, say):
    if (event.get("user") != claudeUserId and (event.get("message") == None or event.get("message").get("user") != claudeUserId)):
        # print("Not claude message event, skipping", event)
        return
    # print("Claude message event", event)
    if (event["type"] == "message" and event.get("thread_ts") != None):
        threadId = event.get("thread_ts")
        created = math.floor(float(event["ts"]))
        ts = event["ts"]
        text = event["text"]
        if (chatMap.get(threadId) == None):
            print("WARNING: ts not found in chat threads", threadId)
            return
        print("Reply match:", threadId, ts, text)
        if (not ts in chatMap[threadId].replies):
            chatMap[threadId].replies.append(ts)
        replyMap[ts] = ChatReply(threadId=threadId, created=created)
        if (not "_Typing…_" in text):
            replyMap[ts].typing = False
        replyMap[ts].created = created
        replyMap[ts].content = text.replace("_Typing…_", "")

    elif (event["type"] == "message" and event.get("subtype") == "message_changed"):
        created = math.floor(float(event["ts"]))
        ts = event["message"]["ts"]
        text = event["message"]["text"]
        if (replyMap.get(ts) == None):
            print("WARNING: ts not found in replyMap", ts)
            return
        threadId = replyMap.get(ts).threadId
        if (chatMap.get(threadId) == None):
            print("WARNING: ts not found in chat threads", threadId)
            return
        print("Edit match:", threadId, ts, text)
        if (not "_Typing…_" in text):
            replyMap[ts].typing = False
        replyMap[ts].created = created
        replyMap[ts].content = text.replace("\n\n_Typing…_", "")

api = FastAPI()


class ChatCompletionMessage(BaseModel):
    role: str
    content: str


class ChatCompletionChoice(BaseModel):
    index: int = 0
    finish_reason: str = "stop"
    message: ChatCompletionMessage


class ChatCompletionResponse(BaseModel):
    id: str
    replies: list
    object: str = "chat.completion"
    created: int
    model: str = "claude"
    choices: list


class ChatCompletionChoiceDelta(BaseModel):
    index: int = 0
    finish_reason: str = None
    delta: dict


class ChatCompletionStreamResponse(BaseModel):
    id: str
    reply: str
    object: str = "chat.completion.chunk"
    created: int
    model: str = "claude"
    choices: list


class ChatCompletionRequest(BaseModel):
    model: str = "claude"
    messages: list
    stream: bool = False
    thread_ts: str = None


class ChatThread(BaseModel):
    replies: list = []
    looping: bool = True


class ChatReply(BaseModel):
    threadId: str
    created: str
    typing: bool = True
    content: str = ""


@api.get("/health")
async def read_root():
    return {"status": "ok"}


@api.post("/v1/chat/completions")
async def chat_completion(payload: ChatCompletionRequest):
    try:
        content = '\n'.join([message['content']
                            for message in payload.messages])
        response = client.chat_postMessage(
            channel=claudeChannelId,
            text=f"<@{claudeUserId}> {content}",
            thread_ts=payload.thread_ts
        )
        threadId = response["ts"]
        if (response.get("message") != None):
            if (response.get("message").get("thread_ts") != None):
                threadId = response.get("message").get("thread_ts")
                print("Reply created: ", threadId)
            elif (response.get("message").get("ts") != None):
                threadId = response.get("message").get("ts")
                print("Thread created: ", threadId)
        chatMap[threadId] = ChatThread()

        if (payload.stream == True):
            def wait_for_response():
                contentHistory = {}
                while (chatMap.get(threadId).looping == True):
                    chat = chatMap.get(threadId)
                    # print("Looping chat thread", chat)
                    typing = False
                    for ts in chat.replies:
                        reply = replyMap.get(ts)
                        curContent = reply.content
                        prevContent = contentHistory.get(ts)
                        if (prevContent == None):
                            prevContent = "_Typing…_"
                        if (curContent != prevContent):
                            diffContent = curContent.replace(prevContent, "")
                            contentHistory[ts] = curContent
                            finishReason = None
                            if (reply.typing == False):
                                finishReason = "stop"
                            data = ChatCompletionStreamResponse(id=threadId, reply=ts, created=reply.created, choices=[
                                                                ChatCompletionChoiceDelta(delta={"content": diffContent}, finish_reason=finishReason)])
                            chunk = 'data: {}\n\n'.format(data.json())
                            # print(chunk)
                            yield chunk
                        if (reply.typing == True):
                            typing = True
                    if (len(chat.replies) > 0 and typing == False):
                        chat.looping = False
                        chunk = 'data: {}\n\n'.format("[DONE]")
                        # print(chunk)
                        yield chunk
                    time.sleep(0.25)
                chatMap.pop(threadId)
            return StreamingResponse(wait_for_response(), media_type="text/event-stream")
        else:
            replies = []
            created = 0
            while (chatMap.get(threadId).looping == True):
                chat = chatMap.get(threadId)
                # print("Looping chat thread", chat)
                typing = False
                for idx, ts in enumerate(chat.replies):
                    reply = replyMap.get(ts)
                    if (len(replies) > idx):
                        replies[idx] = reply.content
                    else:
                        replies.append(reply.content)
                    if (reply.created >= created):
                        created = reply.created
                    if (reply.typing == True):
                        typing = True
                if (len(chat.replies) > 0 and typing == False):
                    chat.looping = False
                await asyncio.sleep(0.25)
            replyContent = '\n'.join(replies)
            data = ChatCompletionResponse(id=threadId, created=created, replies=chatMap.get(threadId).replies, choices=[
                                          ChatCompletionChoice(message=ChatCompletionMessage(role="assistant", content=replyContent))])
            chatMap.pop(threadId)
            return data
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        # str like 'invalid_auth', 'channel_not_found'
        assert e.response["error"]
        print(e.response)
        return
    except KeyboardInterrupt:
        return


try:
    response = client.users_list()
    users = response["members"]
    user = [x for x in users if x["real_name"] == "Claude"][0]
    claudeUserId = user["id"]
    print("Claude user id:", claudeUserId)
    channelName = os.environ.get("CLAUDE_CHANNEL")
    if (channelName != None):
        response = client.conversations_list(exclude_archived=True)
        channels = response["channels"]
        channel = [x for x in channels if x["name"] == channelName][0]
        claudeChannelId = channel["id"]
        print("Claude channel id:", claudeChannelId)
except SlackApiError as e:
    # You will get a SlackApiError if "ok" is False
    # str like 'invalid_auth', 'channel_not_found'
    assert e.response["error"]
    print(e.response)


@api.on_event('startup')
async def start_slack_socket_conn():
    await handler.connect_async()


@api.on_event('shutdown')
async def start_slack_socket_conn():
    await handler.close_async()
