from typing import Annotated, List, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .tools import ALL_TOOLS


class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tool_steps: int
    max_tool_steps: int


def _trim_and_prepend_system(
    messages: List[BaseMessage],
    system_prompt: str,
    history_window: int,
) -> List[BaseMessage]:
    """Aplica janela de historico e prepende SystemMessage.

    Filtra mensagens que nao sao do sistema, aplica o trim baseado
    em history_window (pares human/ai), e coloca o system prompt
    no inicio. Isso e feito antes de chamar o modelo, sem alterar
    o state persistido.
    """
    non_system = [m for m in messages if not isinstance(m, SystemMessage)]

    if history_window > 0:
        # Mantemos a ultima mensagem (HumanMessage atual) + history_window pares anteriores
        # O ultimo elemento e sempre o HumanMessage atual
        max_history_msgs = history_window * 2
        if len(non_system) > max_history_msgs + 1:
            non_system = non_system[-(max_history_msgs + 1):]
    elif history_window == 0:
        # Apenas a mensagem atual
        if non_system:
            non_system = [non_system[-1]]

    return [SystemMessage(content=system_prompt), *non_system]


def build_graph(
    model_name: str,
    system_prompt: str,
    history_window: int,
    checkpointer=None,
):
    model = ChatOpenAI(model=model_name, temperature=0, streaming=True).bind_tools(ALL_TOOLS)
    tool_node = ToolNode(ALL_TOOLS)

    async def assistant_node(state: GraphState) -> dict:
        trimmed = _trim_and_prepend_system(
            state["messages"], system_prompt, history_window,
        )
        response = await model.ainvoke(trimmed)
        return {"messages": [response]}

    async def tools_node(state: GraphState) -> dict:
        result = await tool_node.ainvoke({"messages": state["messages"]})
        return {
            "messages": result["messages"],
            "tool_steps": state.get("tool_steps", 0) + 1,
        }

    def route_after_assistant(state: GraphState) -> str:
        messages = state.get("messages", [])
        if not messages:
            return END

        last_message = messages[-1]
        if (
            isinstance(last_message, AIMessage)
            and last_message.tool_calls
            and state.get("tool_steps", 0) < state.get("max_tool_steps", 0)
        ):
            return "tools"

        return END

    graph_builder = StateGraph(GraphState)
    graph_builder.add_node("assistant", assistant_node)
    graph_builder.add_node("tools", tools_node)
    graph_builder.add_edge(START, "assistant")
    graph_builder.add_conditional_edges("assistant", route_after_assistant)
    graph_builder.add_edge("tools", "assistant")
    return graph_builder.compile(checkpointer=checkpointer)
