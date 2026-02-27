import argparse
from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from .chat import invoke_chat, trim_history
from .config import apply_cli_overrides, load_settings
from .graph import build_graph
from .memory import MemoryStoreError, load_session_history, save_session_history

EXIT_COMMANDS = {"sair", "exit", "quit"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa um chat com LangGraph (single-turn ou multi-turno) "
            "com tool calling basico."
        )
    )
    parser.add_argument(
        "message",
        nargs="?",
        help=(
            "Mensagem unica para enviar ao assistente. "
            "Se vazio, abre chat interativo."
        ),
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Quantidade de turnos na memoria curta do chat interativo.",
    )
    parser.add_argument(
        "--max-tool-steps",
        type=int,
        default=None,
        help="Limite de ciclos de tool calling por resposta.",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Identificador da sessao para memoria persistente.",
    )
    parser.add_argument(
        "--memory-file",
        default=None,
        help="Arquivo JSON de memoria persistente.",
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Desativa leitura e escrita da memoria persistente nesta execucao.",
    )
    return parser.parse_args()


def _load_history(memory_file: str, session_id: str) -> tuple[List[BaseMessage], bool]:
    try:
        return load_session_history(memory_file, session_id), True
    except MemoryStoreError as exc:
        print(f"Aviso: {exc}. Memoria persistente desativada nesta execucao.")
        return [], False


def _save_history(memory_file: str, session_id: str, history: List[BaseMessage]) -> None:
    try:
        save_session_history(memory_file, session_id, history)
    except MemoryStoreError as exc:
        print(f"Aviso: {exc}. Nao foi possivel salvar a memoria desta sessao.")


def run_interactive_chat(
    graph,
    system_prompt: str,
    max_turns: int,
    max_tool_steps: int,
    history: List[BaseMessage],
    memory_file: str | None,
    session_id: str,
) -> None:
    print(
        "Modo chat iniciado. Digite 'sair' para encerrar. "
        f"Memoria curta: {max_turns} turno(s). "
        f"Limite de tool steps: {max_tool_steps}."
    )

    while True:
        try:
            user_input = input("Voce: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            return

        if not user_input:
            continue

        if user_input.lower() in EXIT_COMMANDS:
            print("Encerrando.")
            return

        prompt_history = trim_history(history, max_turns)
        answer = invoke_chat(
            graph=graph,
            system_prompt=system_prompt,
            history=prompt_history,
            user_input=user_input,
            max_tool_steps=max_tool_steps,
        )
        print(f"Jarvis: {answer}")

        history.extend(
            [
                HumanMessage(content=user_input),
                AIMessage(content=answer),
            ]
        )

        if memory_file is not None:
            _save_history(memory_file, session_id, history)


def main() -> None:
    args = parse_args()
    settings = apply_cli_overrides(
        load_settings(),
        max_turns=args.max_turns,
        max_tool_steps=args.max_tool_steps,
        session_id=args.session_id,
        memory_file=args.memory_file,
        disable_memory=args.no_memory,
    )

    graph = build_graph(settings.model_name)
    memory_file = settings.memory_file if settings.persist_memory else None
    history: List[BaseMessage] = []

    if memory_file is not None:
        history, memory_enabled = _load_history(memory_file, settings.session_id)
        if not memory_enabled:
            memory_file = None

    if args.message:
        prompt_history = trim_history(history, settings.history_window)
        answer = invoke_chat(
            graph=graph,
            system_prompt=settings.system_prompt,
            history=prompt_history,
            user_input=args.message,
            max_tool_steps=settings.max_tool_steps,
        )
        print(f"Jarvis: {answer}")

        if memory_file is not None:
            history.extend(
                [
                    HumanMessage(content=args.message),
                    AIMessage(content=answer),
                ]
            )
            _save_history(memory_file, settings.session_id, history)
        return

    if memory_file is not None:
        loaded_turns = len(history) // 2
        print(
            f"Sessao: {settings.session_id} | "
            f"Historico carregado: {loaded_turns} turno(s)."
        )

    run_interactive_chat(
        graph=graph,
        system_prompt=settings.system_prompt,
        max_turns=settings.history_window,
        max_tool_steps=settings.max_tool_steps,
        history=history,
        memory_file=memory_file,
        session_id=settings.session_id,
    )


if __name__ == "__main__":
    main()
