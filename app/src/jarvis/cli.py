import argparse

from langgraph.checkpoint.sqlite import SqliteSaver
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from .chat import stream_chat
from .config import apply_cli_overrides, load_settings
from .graph import build_graph

EXIT_COMMANDS = {"sair", "exit", "quit"}


def _stream_response(
    console: Console,
    graph,
    user_input: str,
    max_tool_steps: int,
    thread_id: str,
) -> None:
    console.print("Jarvis:")
    accumulated = ""
    with Live(Markdown(""), refresh_per_second=8, console=console) as live:
        for token in stream_chat(
            graph=graph,
            user_input=user_input,
            max_tool_steps=max_tool_steps,
            thread_id=thread_id,
        ):
            accumulated += token
            live.update(Markdown(accumulated))
    if not accumulated:
        console.print("Nao foi possivel gerar resposta.")


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
        "--no-memory",
        action="store_true",
        help="Desativa leitura e escrita da memoria persistente nesta execucao.",
    )
    return parser.parse_args()


def run_interactive_chat(
    console: Console,
    graph,
    max_tool_steps: int,
    session_id: str,
    history_window: int,
) -> None:
    print(
        "Modo chat iniciado. Digite 'sair' para encerrar. "
        f"Memoria curta: {history_window} turno(s). "
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

        _stream_response(
            console=console,
            graph=graph,
            user_input=user_input,
            max_tool_steps=max_tool_steps,
            thread_id=session_id,
        )


def main() -> None:
    args = parse_args()
    settings = apply_cli_overrides(
        load_settings(),
        max_turns=args.max_turns,
        max_tool_steps=args.max_tool_steps,
        session_id=args.session_id,
        disable_memory=args.no_memory,
    )

    conn_string = settings.db_path if settings.persist_memory else ":memory:"
    console = Console()

    with SqliteSaver.from_conn_string(conn_string) as checkpointer:
        graph = build_graph(
            model_name=settings.model_name,
            system_prompt=settings.system_prompt,
            history_window=settings.history_window,
            checkpointer=checkpointer,
        )

        if args.message:
            _stream_response(
                console=console,
                graph=graph,
                user_input=args.message,
                max_tool_steps=settings.max_tool_steps,
                thread_id=settings.session_id,
            )
            return

        if settings.persist_memory:
            print(f"Sessao: {settings.session_id}")

        run_interactive_chat(
            console=console,
            graph=graph,
            max_tool_steps=settings.max_tool_steps,
            session_id=settings.session_id,
            history_window=settings.history_window,
        )


if __name__ == "__main__":
    main()
