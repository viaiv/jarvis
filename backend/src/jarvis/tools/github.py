"""Ferramentas GitHub para o agente Jarvis.

Permite ler issues, explorar codigo, criar branches, commitar arquivos e abrir PRs.
Dependencia opcional: pip install PyGithub (ou pip install -e './backend[github]')
"""

from __future__ import annotations

import base64
import os
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from github import Github


def _get_client() -> "Github":
    """Retorna cliente PyGithub autenticado."""
    try:
        from github import Github
    except ImportError:
        raise RuntimeError(
            "PyGithub nao instalado. Execute: pip install -e './backend[github]'"
        )

    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN nao configurado. Defina no arquivo .env."
        )
    return Github(token)


@tool
def github_read_issue(repo: str, issue_number: int) -> str:
    """Le titulo, corpo e labels de uma issue do GitHub.

    Args:
        repo: Repositorio no formato 'owner/repo' (ex: 'viaiv/jarvis').
        issue_number: Numero da issue.
    """
    try:
        gh = _get_client()
        repository = gh.get_repo(repo)
        issue = repository.get_issue(issue_number)
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Erro ao ler issue #{issue_number} de {repo}: {e}"

    labels = ", ".join(label.name for label in issue.labels) or "nenhuma"
    body = issue.body or "(sem descricao)"

    return (
        f"Issue #{issue.number}: {issue.title}\n"
        f"Estado: {issue.state}\n"
        f"Labels: {labels}\n"
        f"Autor: {issue.user.login}\n"
        f"---\n{body}"
    )


@tool
def github_read_file(repo: str, path: str, branch: str = "") -> str:
    """Le o conteudo de um arquivo de um repositorio GitHub.

    Args:
        repo: Repositorio no formato 'owner/repo'.
        path: Caminho do arquivo no repositorio (ex: 'src/main.py').
        branch: Branch para ler. Vazio = branch default.
    """
    try:
        gh = _get_client()
        repository = gh.get_repo(repo)
        ref = branch or repository.default_branch
        contents = repository.get_contents(path, ref=ref)
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Erro ao ler {path} de {repo}: {e}"

    if isinstance(contents, list):
        return f"'{path}' e um diretorio. Use github_list_files para listar."

    decoded = contents.decoded_content.decode("utf-8", errors="replace")

    # Limitar tamanho para nao estourar contexto do LLM
    max_chars = 15000
    if len(decoded) > max_chars:
        decoded = decoded[:max_chars] + f"\n\n... (truncado, {len(decoded)} chars total)"

    return f"Arquivo: {path} (branch: {ref})\n---\n{decoded}"


@tool
def github_list_files(repo: str, path: str = "", branch: str = "") -> str:
    """Lista arquivos e diretorios de um caminho no repositorio GitHub.

    Args:
        repo: Repositorio no formato 'owner/repo'.
        path: Caminho do diretorio. Vazio = raiz do repositorio.
        branch: Branch para listar. Vazio = branch default.
    """
    try:
        gh = _get_client()
        repository = gh.get_repo(repo)
        ref = branch or repository.default_branch
        contents = repository.get_contents(path, ref=ref)
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Erro ao listar {path} de {repo}: {e}"

    if not isinstance(contents, list):
        return f"'{path}' e um arquivo, nao um diretorio."

    lines = []
    for item in sorted(contents, key=lambda x: (x.type != "dir", x.name)):
        prefix = "dir " if item.type == "dir" else "    "
        size = f" ({item.size}B)" if item.type == "file" else ""
        lines.append(f"{prefix}{item.path}{size}")

    header = f"Conteudo de '{path or '/'}' (branch: {ref}) - {len(contents)} itens:"
    return header + "\n" + "\n".join(lines)


@tool
def github_comment_issue(repo: str, issue_number: int, body: str) -> str:
    """Adiciona um comentario em uma issue do GitHub.

    Args:
        repo: Repositorio no formato 'owner/repo'.
        issue_number: Numero da issue.
        body: Texto do comentario (suporta Markdown).
    """
    if not body.strip():
        return "Erro: corpo do comentario nao pode ser vazio."

    try:
        gh = _get_client()
        repository = gh.get_repo(repo)
        issue = repository.get_issue(issue_number)
        comment = issue.create_comment(body)
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Erro ao comentar na issue #{issue_number}: {e}"

    return f"Comentario criado na issue #{issue_number} (id: {comment.id})."


@tool
def github_create_branch(repo: str, branch: str, from_branch: str = "") -> str:
    """Cria uma nova branch no repositorio GitHub.

    Args:
        repo: Repositorio no formato 'owner/repo'.
        branch: Nome da nova branch (ex: 'fix/42').
        from_branch: Branch de origem. Vazio = branch default.
    """
    if not branch.strip():
        return "Erro: nome da branch nao pode ser vazio."

    try:
        gh = _get_client()
        repository = gh.get_repo(repo)
        source = from_branch or repository.default_branch
        source_ref = repository.get_git_ref(f"heads/{source}")
        sha = source_ref.object.sha
        repository.create_git_ref(ref=f"refs/heads/{branch}", sha=sha)
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Erro ao criar branch '{branch}': {e}"

    return f"Branch '{branch}' criada a partir de '{source}' (sha: {sha[:8]})."


@tool
def github_create_or_update_file(
    repo: str,
    path: str,
    message: str,
    content: str,
    branch: str,
) -> str:
    """Cria ou atualiza um arquivo no repositorio GitHub.

    Args:
        repo: Repositorio no formato 'owner/repo'.
        path: Caminho do arquivo (ex: 'src/fix.py').
        message: Mensagem de commit.
        content: Conteudo do arquivo.
        branch: Branch onde salvar o arquivo.
    """
    if not branch.strip():
        return "Erro: branch e obrigatoria para criar/atualizar arquivos."
    if not message.strip():
        return "Erro: mensagem de commit nao pode ser vazia."

    try:
        gh = _get_client()
        repository = gh.get_repo(repo)

        # Verificar se arquivo ja existe para update
        try:
            existing = repository.get_contents(path, ref=branch)
            if isinstance(existing, list):
                return f"Erro: '{path}' e um diretorio, nao um arquivo."
            result = repository.update_file(
                path=path,
                message=message,
                content=content,
                sha=existing.sha,
                branch=branch,
            )
            return (
                f"Arquivo atualizado: {path}\n"
                f"Commit: {result['commit'].sha[:8]}\n"
                f"Branch: {branch}"
            )
        except Exception:
            # Arquivo nao existe, criar
            result = repository.create_file(
                path=path,
                message=message,
                content=content,
                branch=branch,
            )
            return (
                f"Arquivo criado: {path}\n"
                f"Commit: {result['commit'].sha[:8]}\n"
                f"Branch: {branch}"
            )

    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Erro ao salvar {path}: {e}"


@tool
def github_create_pr(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "",
) -> str:
    """Abre um Pull Request como draft no repositorio GitHub.

    Args:
        repo: Repositorio no formato 'owner/repo'.
        title: Titulo do PR.
        body: Descricao do PR (suporta Markdown).
        head: Branch com as mudancas.
        base: Branch de destino. Vazio = branch default.
    """
    if not title.strip():
        return "Erro: titulo do PR nao pode ser vazio."
    if not head.strip():
        return "Erro: branch head e obrigatoria."

    try:
        gh = _get_client()
        repository = gh.get_repo(repo)
        base_branch = base or repository.default_branch

        pr = repository.create_pull(
            title=title,
            body=body,
            head=head,
            base=base_branch,
            draft=True,
        )
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Erro ao criar PR: {e}"

    return (
        f"PR #{pr.number} criado (draft): {pr.title}\n"
        f"{head} -> {base_branch}\n"
        f"URL: {pr.html_url}"
    )


@tool
def github_add_label(repo: str, issue_number: int, label: str) -> str:
    """Adiciona uma label a uma issue ou PR no GitHub.

    Args:
        repo: Repositorio no formato 'owner/repo'.
        issue_number: Numero da issue ou PR.
        label: Nome da label a adicionar.
    """
    if not label.strip():
        return "Erro: nome da label nao pode ser vazio."

    try:
        gh = _get_client()
        repository = gh.get_repo(repo)
        issue = repository.get_issue(issue_number)
        issue.add_to_labels(label)
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Erro ao adicionar label '{label}' na issue #{issue_number}: {e}"

    return f"Label '{label}' adicionada na issue #{issue_number}."


GITHUB_TOOLS = [
    github_read_issue,
    github_read_file,
    github_list_files,
    github_comment_issue,
    github_create_branch,
    github_create_or_update_file,
    github_create_pr,
    github_add_label,
]
