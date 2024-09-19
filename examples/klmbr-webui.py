"""
title: klmbr
author: av
author_url: https://github.com/av
description: klmbr - inducing creativity via forced retokenization
version: 0.0.1
"""

import logging
import re
import json
import random

from typing import (
    Generator,
    Iterator,
    AsyncGenerator,
    Callable,
    Awaitable,
    Any,
    List,
    Dict,
)

from open_webui.constants import TASKS
from open_webui.apps.ollama import main as ollama

# ===============================================================================

def setup_logger():
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.set_name("ol1")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


mods = [
    "capitalize",
    "diacritic",
    "leetspeak",
    # "remove_vowel",
]

def modify_text(text, percentage):
    if not text:
        return "", {}  # Return empty string and empty mapping if input is empty

    if not 0 <= percentage <= 100:
        raise ValueError("Percentage must be between 0 and 100")

    words = text.split()
    chars = list(text)
    num_chars_to_modify = max(1, int(len(chars) * (percentage / 100)))
    indices_to_modify = random.sample(range(len(chars)), num_chars_to_modify)
    word_mapping = {}

    for idx in indices_to_modify:
        modification = random.choice(mods)

        # Find the word that contains the current character
        current_length = 0
        for word_idx, word in enumerate(words):
            if current_length <= idx < current_length + len(word):
                original_word = word
                word_start_idx = current_length
                break
            current_length += len(word) + 1  # +1 for the space
        else:
            # If we're here, we're likely dealing with a space or the last character
            continue

        if modification == "capitalize":
            chars[idx] = chars[idx].swapcase()
        elif modification == "diacritic":
            if chars[idx].isalpha():
                diacritics = ["̀", "́", "̂", "̃", "̈", "̄", "̆", "̇", "̊", "̋"]
                chars[idx] = chars[idx] + random.choice(diacritics)
        elif modification == "leetspeak":
            leetspeak_map = {
                "a": "4",
                "e": "3",
                "i": "1",
                "o": "0",
                "s": "5",
                "t": "7",
                "b": "8",
                "g": "9",
                "l": "1",
            }
            chars[idx] = leetspeak_map.get(chars[idx].lower(), chars[idx])
        elif modification == "remove_vowel":
            if chars[idx].lower() in "aeiou":
                chars[idx] = ""

        modified_word = "".join(
            chars[word_start_idx : word_start_idx + len(original_word)]
        )

        if modified_word != original_word:
            # Clean up both the modified word and the original word
            cleaned_modified_word = modified_word.rstrip(".,!?")
            cleaned_original_word = original_word.rstrip(".,!?")
            word_mapping[cleaned_modified_word] = cleaned_original_word

    modified_text = "".join(chars)
    return modified_text, word_mapping


def replace_with_mapping(text, mapping):
    for key, value in mapping.items():
        text = text.replace(key, value)
    return text


logger = setup_logger()

# ===============================================================================

name = "klmbr"

class Pipe:
    def __init__(self):
        self.type = "manifold"

    def pipes(self) -> list[dict[str, str]]:
        ollama.get_all_models()
        models = ollama.app.state.MODELS

        out = [
            {"id": f"{name}-{key}", "name": f"{name} {models[key]['name']}"}
            for key in models
        ]
        logger.debug(f"Available models: {out}")

        return out

    def resolve_model(self, body: dict) -> str:
        return body.get("model").replace(f"{name}.{name}-", "")

    def resolve_question(self, body: dict) -> str:
        return body.get("messages")[-1].get("content")

    async def pipe(
        self, body: dict, __user__: dict, __event_emitter__=None, __task__=None
    ) -> str | Generator | Iterator:
        model = self.resolve_model(body)

        if __task__ == TASKS.TITLE_GENERATION:
            return await self.get_completion(model, body.get("messages"))

        # TODO: concurrency
        self.__current_event_emitter__ = __event_emitter__

        original = self.resolve_question(body)
        rewritten, mapping = modify_text(original, 30)

        async for chunk in self.get_word_stream_completion(
            model,
            [
                {
                    "role": "user",
                    "content": f"Complete my request, do not mention syntax or accent marks:\n{rewritten}\nYour answer has to be syntactically perfect.",
                }
            ],
        ):
            chunk = replace_with_mapping(chunk, mapping)
            await self.emit_message(__event_emitter__, chunk)

        return ""

    async def progress(
        self,
        message: str,
    ):
        await self.emit_status(
            self.__current_event_emitter__,
            "info",
            message,
            False,
        )

    async def done(
        self,
    ):
        await self.emit_status(
            self.__current_event_emitter__,
            "info",
            "Fin.",
            True,
        )

    async def emit_message(
        self,
        __event_emitter__: Callable[[dict], Awaitable[None]],
        message: str,
    ):
        await __event_emitter__({"type": "message", "data": {"content": message}})

    async def emit_replace(
        self,
        __event_emitter__: Callable[[dict], Awaitable[None]],
        message: str,
    ):
        await __event_emitter__({"type": "replace", "data": {"content": message}})

    async def emit_status(
        self,
        __event_emitter__: Callable[[dict], Awaitable[None]],
        level: str,
        message: str,
        done: bool,
    ):
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "status": "complete" if done else "in_progress",
                    "level": level,
                    "description": message,
                    "done": done,
                },
            }
        )

    async def get_streaming_completion(
        self, model: str, messages
    ) -> AsyncGenerator[str, None]:
        response = await ollama.generate_openai_chat_completion(
            {"model": model, "messages": messages, "stream": True}
        )

        async for chunk in response.body_iterator:
            # The chunk is likely a bytes object, so we need to decode it
            chunk_str = chunk.decode("utf-8")

            # The chunk might start with "data: ", so we'll remove that if present
            if chunk_str.startswith("data: "):
                chunk_str = chunk_str[6:]

            # Try to parse the chunk as JSON
            try:
                chunk_data = json.loads(chunk_str)
                if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                    delta = chunk_data["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
            except json.JSONDecodeError:
                # If it's not valid JSON, skip this chunk
                continue

    async def get_word_stream_completion(self, model, messages):
        buffer = ""
        async for chunk in self.get_streaming_completion(model, messages):
            buffer += chunk
            words = re.findall(r"\S+|\n|\s+", buffer)

            for word in words[:-1]:
                yield word

            buffer = words[-1] if words else ""

        if buffer:
            yield buffer

    async def get_completion(self, model: str, messages):
        response = await ollama.generate_openai_chat_completion(
            {"model": model, "messages": messages, "stream": False}
        )

        return response["choices"][0]["message"]["content"]
