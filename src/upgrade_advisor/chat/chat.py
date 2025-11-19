import logging
import os

import requests
from dotenv import load_dotenv

from .prompts import (
    chat_summarizer_prompt,
    query_rewriter_prompt,
    result_package_summary_prompt,
)

load_dotenv()


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


async def query(payload):
    API_URL = "https://router.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['HF_TOKEN']}",
    }
    response = requests.post(API_URL, headers=headers, json=payload, timeout=300)
    return response.json()


def extract_answer_content(answer_content: str) -> str:
    # the thinking model has answers like this:
    # `long multi-step reasoning ending with </think>`
    # so split and return only the final answer part
    if "</think>" in answer_content:
        return answer_content.split("</think>")[-1].strip()
    return answer_content.strip()


async def run_document_qa(
    question: str, context: str, rewritten_question: str = None
) -> str:
    response = await query(
        {
            "messages": [
                {
                    "role": "user",
                    "content": result_package_summary_prompt(
                        context,
                        original_question=question,
                        rewritten_question=rewritten_question,
                    ),
                }
            ],
            # "model": "Qwen/Qwen3-4B-Thinking-2507",
            "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        }
    )

    answer = response["choices"][0]["message"]
    return extract_answer_content(answer["content"])


async def qn_rewriter_judge(original_question: str, rewritten_question: str) -> str:
    response = await query(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
                    You are a judge that evaluates whether a rewritten question
                    captures the intent of the original question.
                    Note that the rewritten question may include details from
                    the chat history, but you should focus on whether the core
                    intent of the original question is preserved. The
                    additional history context will not change the user's intent, but
                    may add clarifications.
                    Return the word "YES" if it does, otherwise "NO". No additional
                    explanation. Never return anything other than "YES" or "NO".

                    EXAMPLE 1:
                    `ORIGINAL QUESTION: latest version of nnumpy?`
                    `REWRITTEN QUESTION: What is the latest version of numpy?`
                    Answer: YES

                    EXAMPLE 2:
                    `ORIGINAL QUESTION: Show me the dev docu link of requests
                    liberary.`
                    `REWRITTEN QUESTION: Show me the user guide of the requests
                    library.`
                    Answer: NO

                    EXAMPLE 3:
                    `ORIGINAL QUESTION: How to install fapi?`
                    `REWRITTEN QUESTION: What is the dependency list of fastapi?`
                    Answer: NO

                    EXAMPLE 4:
                    `ORIGINAL QUESTION: The user had trouble with a version of
                    pandas. User tried downgrading to 1.2.0 but it didn't help
                    and has compatibility issues with other packages like numpy
                    of version 1.19. What version should I use?`
                    `REWRITTEN QUESTION: Which version of pandas is most stable
                    with version 1.19 of numpy?`
                    Answer: YES

                    EXAMPLE 5:
                    `ORIGINAL QUESTION: The user is talking about issues with
                    version 2.0.0 of requests library. They mentioned that it
                    broke their existing code that worked with version numpy 1.2.3. I
                    am looking for a version that is compatible.`
                    `REWRITTEN QUESTION: Which version of requests is compatible
                    with version numpy 1.2.3?`
                    Answer: YES


                    ORIGINAL QUESTION: {original_question}\n
                    REWRITTEN QUESTION: {rewritten_question}\n
                    Answer:
                    """,
                }
            ],
            # "model": "Qwen/Qwen3-4B-Thinking-2507",
            "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        }
    )
    answer = response["choices"][0]["message"]
    answer_text = extract_answer_content(answer["content"])
    logger.info(f"Question Rewriter judge answer: {answer_text}")
    if answer_text.strip().upper() == "YES":
        return True
    else:
        return False


async def qn_rewriter(original_question: str, summarized_history: str = "") -> str:
    response = await query(
        {
            "messages": [
                {
                    "role": "user",
                    "content": query_rewriter_prompt(
                        original_question, summarized_history
                    ),
                }
            ],
            # "model": "Qwen/Qwen3-4B-Thinking-2507",
            "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        }
    )

    answer = response["choices"][0]["message"]
    rewritten_question = extract_answer_content(answer["content"])
    is_good = await qn_rewriter_judge(original_question, rewritten_question)

    return rewritten_question, is_good


async def summarize_chat_history(
    history: list[dict],
    turns_cutoff=10,
    word_cutoff=100,
) -> str:
    # history is a list of dicts with 'role' and 'content' keys
    # [{"role": "user", "content": "..."}, {"role": "assistant", "content":
    # "..."}]
    logger.info(f"Summarizing chat history with {len(history)} turns.")
    logger.info(f"Using last {turns_cutoff} turns with {word_cutoff} words each.")
    chat_history_text = ""
    for turn in history[-turns_cutoff:]:
        # take only the last `cutoff` turns
        role = turn["role"]
        content = turn["content"]
        if len(content.split()) > word_cutoff:
            content = " ".join(content.split()[:word_cutoff]) + " [TRUNCATED]"
        chat_history_text += f"{role.upper()}:\n{content}\n\n"

    logger.info(
        f"Chat history text for summarization ({len(chat_history_text.split())} words)"
    )
    response = await query(
        {
            "messages": [
                {
                    "role": "user",
                    "content": chat_summarizer_prompt(chat_history_text),
                }
            ],
            # "model": "Qwen/Qwen3-4B-Thinking-2507",
            "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        }
    )

    answer = response["choices"][0]["message"]
    summary = extract_answer_content(answer["content"])
    return summary
