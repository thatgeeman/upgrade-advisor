import os

import requests
from dotenv import load_dotenv

from .prompts import query_rewriter_prompt, result_package_summary_prompt

load_dotenv()


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
    question: str, context: str, original_question: str = ""
) -> str:
    response = await query(
        {
            "messages": [
                {
                    "role": "user",
                    "content": result_package_summary_prompt(
                        context,
                        question,
                        original_question,
                    ),
                }
            ],
            # "model": "Qwen/Qwen3-4B-Thinking-2507",
            "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        }
    )

    answer = response["choices"][0]["message"]
    return extract_answer_content(answer["content"])


async def qn_rewriter(original_question: str) -> str:
    response = await query(
        {
            "messages": [
                {
                    "role": "user",
                    "content": query_rewriter_prompt(original_question),
                }
            ],
            # "model": "Qwen/Qwen3-4B-Thinking-2507",
            "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        }
    )

    answer = response["choices"][0]["message"]
    return extract_answer_content(answer["content"])
