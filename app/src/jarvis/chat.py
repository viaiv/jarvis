from typing import Any, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError

TOOL_LIMIT_MESSAGE = (
    "Atingi o limite de chamadas de ferramenta nesta resposta. "
    "Tente simplificar a pergunta."
)


def _render_ai_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    text_parts.append(text)
        if text_parts:
            return "\n".join(text_parts)
    return str(content)


def _get_last_ai_message(messages: List[BaseMessage]) -> AIMessage | None:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def invoke_chat(
    graph,
    system_prompt: str,
    history: List[BaseMessage],
    user_input: str,
    max_tool_steps: int,
) -> str:
    initial_messages: List[BaseMessage] = [
        SystemMessage(content=system_prompt),
        *history,
        HumanMessage(content=user_input),
    ]
    recursion_limit = max(6, 2 * max_tool_steps + 4)

    try:
        result = graph.invoke(
            {
                "messages": initial_messages,
                "tool_steps": 0,
                "max_tool_steps": max_tool_steps,
            },
            config={"recursion_limit": recursion_limit},
        )
    except GraphRecursionError:
        return TOOL_LIMIT_MESSAGE

    final_messages = result.get("messages", [])
    last_ai = _get_last_ai_message(final_messages)
    if last_ai is None:
        return "Nao foi possivel gerar resposta."

    if last_ai.tool_calls:
        return TOOL_LIMIT_MESSAGE

    answer = _render_ai_content(last_ai.content).strip()
    if not answer:
        return "Nao foi possivel gerar resposta."
    return answer


def trim_history(history: List[BaseMessage], max_turns: int) -> List[BaseMessage]:
    if max_turns == 0:
        return []
    return history[-(max_turns * 2) :]
