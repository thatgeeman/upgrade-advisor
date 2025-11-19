def result_package_summary_prompt(
    context, original_question, rewritten_question=None
) -> str:
    user_input = f"""
    DEVELOPER QUESTION:
    {original_question}
    """
    if rewritten_question:
        user_input += f"\nREWRITTEN QUESTION (LLM-generated):\n{rewritten_question}\n"

    return f"""Based on the following context from a package search, provide a
    concise summary of the key findings, issues, and recommendations. Focus on
    the main points that would help a developer understand the
    package and answers their question. Focus on the DEVELOPER QUESTION
    provided. LLM REWRITTEN QUESTION is provided for clarity and to help you
    better understand the intent, but always prioritize the original question.

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
