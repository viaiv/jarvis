from typing import Annotated, List, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .tools import ALL_TOOLS


class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tool_steps: int
    max_tool_steps: int


def build_graph(model_name: str):
    model = ChatOpenAI(model=model_name, temperature=0).bind_tools(ALL_TOOLS)
    tool_node = ToolNode(ALL_TOOLS)

    def assistant_node(state: GraphState) -> dict:
        response = model.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(state: GraphState) -> dict:
        result = tool_node.invoke({"messages": state["messages"]})
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
    return graph_builder.compile()
