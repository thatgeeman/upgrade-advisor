def result_package_summary_prompt(context, question, original_question="") -> str:
    return f"""Based on the following context from a package search, provide a
    concise summary of the key findings, issues, and recommendations. Focus on
    the most critical points that would help a developer understand the
    package and answers their question. Focus on the DEVELOPER QUESTION
    provided. LLM REWRITTEN QUESTION is provided for clarity, but the original
    intent should be prioritized.
    CONTEXT:
    {context}
    DEVELOPER QUESTION:
    {original_question}
    LLM REWRITTEN QUESTION:
    {question}

    SUMMARY:
    """


def query_rewriter_prompt(original_question: str) -> str:
    return f"""
    You are a query rewriting agent that reformulates user questions
    about Python packages to be more specific and clear.
    You also aim to remove any typos in the text. You focus the
    typos made about the package metadata,
    versioning, repository or website URLs.
    This will help downstream agents provide more accurate and relevant answers.

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

    REWRITTEN QUESTION:
    """
