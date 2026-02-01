import logging
import os

import requests
from dotenv import load_dotenv

from ..config import CHAT_MODEL

from .prompts import (
    chat_summarizer_prompt,
    query_rewriter_prompt,
    result_package_summary_prompt,
    rewriter_judge_prompt,
)

load_dotenv()


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


async def query(payload, token=None):
    API_URL = "https://router.huggingface.co/v1/chat/completions"
    token = token or os.environ.get("HF_TOKEN", "")  # use passed token or env var
    if token is None or token == "":
        logger.error("No Huggingface token provided for API request.")

    headers = {
        "Authorization": f"Bearer {token}",
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=1000)
    except Exception as e:
        logger.error(f"Error during API request: {e}")
        raise e
    return response.json()


def parse_response(response_json):
    try:
        assert "choices" in response_json, "No 'choices' key in response"
        answer = response_json["choices"][0]["message"]
        return answer
    except AssertionError as e:
        logger.error(f"Assertion error: {e}")
        return {
            "role": "assistant",
            "content": f"""
                Sorry, I couldn't parse the response from huggingface due to
                missing data.
                The API has responded in an unexpected format: {response_json}.
                Please try again later.
                """,
        }
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing response JSON: {e}")
        return {
            "role": "assistant",
            "content": """
                Sorry, I couldn't process the response from huggingface.
                The backend service has failed me. Please try again later.""",
        }
    except Exception as e:
        logger.error(f"Unexpected error parsing response JSON: {e}")
        return {
            "role": "assistant",
            "content": """
                Sorry, I couldn't process your request due to an unexpected error.
                The backend service has failed me. Please try again later.""",
        }


def extract_answer_content(answer_content: str) -> str:
    # the thinking model has answers like this:
    # `long multi-step reasoning ending with </think>`
    # so split and return only the final answer part
    if "</think>" in answer_content:
        return answer_content.split("</think>")[-1].strip()
    return answer_content.strip()


async def run_document_qa(
    question: str, context: str, rewritten_question: str = None, token: str = None
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
                },
            ],
            "model": CHAT_MODEL,
        },
        token=token,
    )

    answer = parse_response(response)
    return extract_answer_content(answer["content"])


async def qn_rewriter_judge(
    original_question: str, rewritten_question: str, token: str = None
) -> str:
    response = await query(
        {
            "messages": [
                {
                    "role": "user",
                    "content": rewriter_judge_prompt(
                        original_question, rewritten_question
                    ),
                },
            ],
            "model": CHAT_MODEL,
        },
        token=token,
    )
    answer = parse_response(response)
    answer_text = extract_answer_content(answer["content"])
    logger.info(f"Question Rewriter judge answer: {answer_text}")
    if answer_text.strip().upper() == "YES":
        return True
    else:
        return False


async def qn_rewriter(
    original_question: str, summarized_history: str = "", token: str = None
) -> str:
    response = await query(
        {
            "messages": [
                {
                    "role": "user",
                    "content": query_rewriter_prompt(
                        original_question, summarized_history
                    ),
                },
            ],
            "model": CHAT_MODEL,
        },
        token=token,
    )

    answer = parse_response(response)
    rewritten_question = extract_answer_content(answer["content"])
    is_good = await qn_rewriter_judge(
        original_question, rewritten_question, token=token
    )

    return rewritten_question, is_good

def get_maybe_truncated(text, word_cutoff):
    """Check if the length of words is large and return truncated if necessary"""
    if len(text.split()) > word_cutoff:
        text = " ".join(text.split()[:word_cutoff]) + " [TRUNCATED]"
    return text

async def summarize_chat_history(
    history: list[dict],
    turns_cutoff=10,
    word_cutoff=100,
    token: str = None,
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
        if isinstance(content, list):
            # content can be a list of type [{'text': ..., 'type':text}, ...]
            # for each text chunk, take only word_cutoff
            content = ' '.join([get_maybe_truncated(c['text']) for c in content])
        content = get_maybe_truncated(content)
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
                },
            ],
            "model": CHAT_MODEL,
        },
        token=token,
    )

    answer = parse_response(response)
    summary = extract_answer_content(answer["content"])
    return summary
