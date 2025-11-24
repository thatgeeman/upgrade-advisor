def result_package_summary_prompt(
    context, original_question, rewritten_question=None
) -> str:
    user_input = f"""
    DEVELOPER QUESTION:
    {original_question}
    """
    if rewritten_question:
        user_input += f"\nREWRITTEN QUESTION (LLM-generated):\n{rewritten_question}\n"

    return f"""You must answer the DEVELOPER QUESTION using only the CONTEXT
    provided. Treat the CONTEXT as the single source of truth, even if it
    conflicts with your training data or expectations about package versions.

    Requirements:
    - Do not add speculation, hedging, or disclaimers.
    - Do not try to fix numbers, dates, package names, or versions unless
    they are clearly typos.
    - Do not mention the CONTEXT, your knowledge cutoff, or phrases like "according
      to the provided context."
    - DO NOT refer to the CONTEXT as "context" in your answer, just use
      "information available about the package" or similar phrases.
    - Write a concise, direct answer that surfaces key findings, issues, and
      recommendations for the developer.
    - If an item is missing from the CONTEXT, say that it is not mentioned rather
      than guessing.
    - Prioritize the original DEVELOPER QUESTION; the LLM REWRITTEN QUESTION is only
      a hint for intent.

    CONTEXT:
    {context}

    {user_input}

    SUMMARY:
    """


def query_rewriter_prompt(original_question: str, summarized_history: str = "") -> str:
    if not summarized_history:
        summarized_history = "<NO PRIOR CHAT HISTORY>"
    # construct the prompt
    return f"""
    You are a query rewriting agent that reformulates user questions
    about Python packages to be more specific and clear.
    You also aim to remove any typos in the text.
    You focus the
    typos made about the package metadata,
    versioning, repository or website URLs.
    This will help downstream agents provide more accurate and relevant
    answers.

    ABOUT USING CHAT HISTORY:
    Use the summarized chat history to provide context for rewriting.
    Maybe the user has already asked related questions and you can use that
    context to improve the question. If the history is not relevant, just focus
    on improving the question itself.

    VERY IMPORTANT:
    - NEVER introduce new information that was not in the original question.
    - Be careful that you do not change the intent of the question.
    - Python packages can have complex names, so do not "correct" package names
    unless there is a clear typo, and even then be cautious.
    - DO NOT change version numbers unless there is an obvious typo, like a
    comma instead of a dot.
    - NEVER ask for clarification from the developer; just rewrite based on
    the given text. The original question is anyway provided downstream.

    ORIGINAL QUESTION:
    {original_question}

    SUMMARIZED CHAT HISTORY:
    {summarized_history}

    REWRITTEN QUESTION:
    """


def chat_summarizer_prompt(chat_history: str) -> str:
    return f"""
    You are a technical chat history summarization agent that condenses a conversation
    between a user and an assistant about Python packages into a concise summary.
    The summary should capture the main topics discussed, questions asked,
    and any important context that would help understand the user's intent.

    IMPORTANT GUIDELINES:
    - Focus on specific packages, versions, issues discussed and any technical details.
    - Emphasize any problems or challenges the user mentioned.
    - Capture the user's goals or what they are trying to achieve.
    - Omit any pleasantries or small talk; just focus on the technical content.
    - Use bullet points or short sentences for clarity.
    - Keep it brief and to the point, ideally under 100 words.

    CHAT HISTORY:
    {chat_history}

    SUMMARY:
    """


def rewriter_judge_prompt(original_question: str, rewritten_question: str) -> str:
    return f"""
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
    """
