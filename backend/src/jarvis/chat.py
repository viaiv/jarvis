from typing import Any, AsyncGenerator, List

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
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


async def invoke_chat(
    graph,
    user_input: str,
    max_tool_steps: int,
    thread_id: str,
) -> str:
    recursion_limit = max(6, 2 * max_tool_steps + 4)

    try:
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=user_input)],
                "tool_steps": 0,
                "max_tool_steps": max_tool_steps,
            },
            config={
                "recursion_limit": recursion_limit,
                "configurable": {"thread_id": thread_id},
            },
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


async def stream_chat(
    graph,
    user_input: str,
    max_tool_steps: int,
    thread_id: str,
) -> AsyncGenerator[dict, None]:
    """Stream eventos tipados do grafo (token, tool_start, tool_end)."""
    recursion_limit = max(6, 2 * max_tool_steps + 4)

    emitted = False
    hit_tool_limit = False
    emitted_tool_ids: set[str] = set()

    try:
        async for chunk, metadata in graph.astream(
            {
                "messages": [HumanMessage(content=user_input)],
                "tool_steps": 0,
                "max_tool_steps": max_tool_steps,
            },
            config={
                "recursion_limit": recursion_limit,
                "configurable": {"thread_id": thread_id},
            },
            stream_mode="messages",
        ):
            node = metadata.get("langgraph_node")

            if node == "assistant" and isinstance(chunk, AIMessageChunk):
                tool_chunks = getattr(chunk, "tool_call_chunks", None)
                if tool_chunks:
                    for tc in tool_chunks:
                        name = tc.get("name")
                        call_id = tc.get("id")
                        if name and call_id and call_id not in emitted_tool_ids:
                            emitted_tool_ids.add(call_id)
                            yield {
                                "type": "tool_start",
                                "name": name,
                                "call_id": call_id,
                            }
                    hit_tool_limit = True
                    continue

                if chunk.content:
                    text = chunk.content if isinstance(chunk.content, str) else ""
                    if text:
                        hit_tool_limit = False
                        emitted = True
                        yield {"type": "token", "content": text}

            elif node == "tools" and isinstance(chunk, ToolMessage):
                tool_name = chunk.name or ""
                call_id = chunk.tool_call_id or ""
                output = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                yield {
                    "type": "tool_end",
                    "name": tool_name,
                    "call_id": call_id,
                    "output": output,
                }

    except GraphRecursionError:
        yield {"type": "token", "content": TOOL_LIMIT_MESSAGE}
        return

    if hit_tool_limit and not emitted:
        yield {"type": "token", "content": TOOL_LIMIT_MESSAGE}
        return

    if not emitted:
        yield {"type": "token", "content": "Nao foi possivel gerar resposta."}
