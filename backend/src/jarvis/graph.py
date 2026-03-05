from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .nodes.classifier import IssueCategory, classify_issue
from .tools import ALL_TOOLS
from .tools.github import GITHUB_TOOLS


class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tool_steps: int
    max_tool_steps: int


def _sanitize_tool_sequences(messages: List[BaseMessage]) -> List[BaseMessage]:
    """Remove sequencias invalidas de tool calls.

    A API da OpenAI exige que:
    - Todo ToolMessage tenha um AIMessage(tool_calls) precedente com tool_call_id correspondente
    - Todo AIMessage(tool_calls) tenha ToolMessages para todos os seus tool_call_ids

    Percorre a lista e remove blocos incompletos (AIMessage(tool_calls) + ToolMessages parciais).
    """
    result: List[BaseMessage] = []
    i = 0

    while i < len(messages):
        msg = messages[i]

        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            expected_ids = {tc["id"] for tc in msg.tool_calls}

            tool_msgs: List[BaseMessage] = []
            j = i + 1
            while j < len(messages) and isinstance(messages[j], ToolMessage):
                tool_msgs.append(messages[j])
                j += 1

            response_ids = {
                tm.tool_call_id
                for tm in tool_msgs
                if isinstance(tm, ToolMessage)
            }

            if expected_ids <= response_ids:
                result.append(msg)
                result.extend(tool_msgs)
            # Senao descarta o bloco inteiro (AIMessage + ToolMessages parciais)
            i = j

        elif isinstance(msg, ToolMessage):
            # ToolMessage orfa (sem AIMessage precedente) — descarta
            i += 1

        else:
            result.append(msg)
            i += 1

    return result


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
        # Conta apenas turnos humanos (HumanMessage) ao inves de todas as mensagens.
        # Isso evita que tool calls (AIMessage+ToolMessage) consumam a janela de contexto.
        human_indices = [
            i for i, m in enumerate(non_system) if isinstance(m, HumanMessage)
        ]

        if len(human_indices) > history_window + 1:
            # Manter os ultimos (history_window + 1) turnos humanos
            # +1 porque o ultimo e a mensagem atual do usuario
            cut_index = human_indices[-(history_window + 1)]
            non_system = non_system[cut_index:]
    elif history_window == 0:
        # Apenas a mensagem atual
        if non_system:
            non_system = [non_system[-1]]

    non_system = _sanitize_tool_sequences(non_system)

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


# ---------------------------------------------------------------------------
# GitHub Agent Graph
# ---------------------------------------------------------------------------

class GitHubGraphState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tool_steps: int
    max_tool_steps: int
    issue_title: str
    issue_body: str
    issue_number: int
    repo: str
    issue_category: Optional[IssueCategory]


def build_github_graph(
    model_name: str,
    system_prompt: str,
    max_tool_steps: int = 15,
    checkpointer=None,
):
    """Constroi grafo do agente GitHub com classificador como entry point.

    Fluxo: START -> classifier -> assistant -> [tools -> assistant]* -> END
    """
    model = ChatOpenAI(
        model=model_name, temperature=0, streaming=True,
    ).bind_tools(GITHUB_TOOLS)
    tool_node = ToolNode(GITHUB_TOOLS)

    async def classifier_node(state: GitHubGraphState) -> dict:
        """Classifica a issue e injeta contexto no historico."""
        category = await classify_issue(
            title=state["issue_title"],
            body=state.get("issue_body", ""),
            model_name=model_name,
        )

        # Montar mensagem inicial para o agente com contexto da issue
        issue_context = (
            f"Issue #{state['issue_number']} no repositorio {state['repo']}\n"
            f"Categoria: {category}\n"
            f"Titulo: {state['issue_title']}\n\n"
            f"Corpo:\n{state.get('issue_body') or '(sem descricao)'}"
        )

        return {
            "issue_category": category,
            "messages": [HumanMessage(content=issue_context)],
        }

    async def assistant_node(state: GitHubGraphState) -> dict:
        trimmed = [SystemMessage(content=system_prompt)] + [
            m for m in state["messages"] if not isinstance(m, SystemMessage)
        ]
        trimmed = _sanitize_tool_sequences(trimmed)
        response = await model.ainvoke(trimmed)
        return {"messages": [response]}

    async def tools_node(state: GitHubGraphState) -> dict:
        result = await tool_node.ainvoke({"messages": state["messages"]})
        return {
            "messages": result["messages"],
            "tool_steps": state.get("tool_steps", 0) + 1,
        }

    def route_after_assistant(state: GitHubGraphState) -> str:
        messages = state.get("messages", [])
        if not messages:
            return END

        last_message = messages[-1]
        if (
            isinstance(last_message, AIMessage)
            and last_message.tool_calls
            and state.get("tool_steps", 0) < state.get("max_tool_steps", max_tool_steps)
        ):
            return "tools"

        return END

    graph_builder = StateGraph(GitHubGraphState)
    graph_builder.add_node("classifier", classifier_node)
    graph_builder.add_node("assistant", assistant_node)
    graph_builder.add_node("tools", tools_node)
    graph_builder.add_edge(START, "classifier")
    graph_builder.add_edge("classifier", "assistant")
    graph_builder.add_conditional_edges("assistant", route_after_assistant)
    graph_builder.add_edge("tools", "assistant")
    return graph_builder.compile(checkpointer=checkpointer)
