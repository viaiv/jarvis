"""Testes para as tools GitHub do Jarvis."""

from unittest.mock import MagicMock, patch

import pytest

from jarvis.tools.github import (
    GITHUB_TOOLS,
    github_add_label,
    github_comment_issue,
    github_create_branch,
    github_create_or_update_file,
    github_create_pr,
    github_list_files,
    github_read_file,
    github_read_issue,
)


def _mock_github():
    """Retorna mock do cliente PyGithub."""
    return MagicMock()


class TestGithubToolsRegistry:
    def test_all_tools_registered(self):
        assert len(GITHUB_TOOLS) == 8

    def test_tool_names(self):
        names = {t.name for t in GITHUB_TOOLS}
        expected = {
            "github_read_issue",
            "github_read_file",
            "github_list_files",
            "github_comment_issue",
            "github_create_branch",
            "github_create_or_update_file",
            "github_create_pr",
            "github_add_label",
        }
        assert names == expected


class TestGithubReadIssue:
    @patch("jarvis.tools.github._get_client")
    def test_read_issue_success(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        mock_issue = MagicMock()
        mock_issue.number = 42
        mock_issue.title = "Bug no login"
        mock_issue.state = "open"
        mock_issue.body = "O login falha com senha correta"
        mock_issue.user.login = "testuser"

        mock_label = MagicMock()
        mock_label.name = "bug"
        mock_issue.labels = [mock_label]

        gh.get_repo.return_value.get_issue.return_value = mock_issue

        result = github_read_issue.invoke({"repo": "viaiv/jarvis", "issue_number": 42})

        assert "Bug no login" in result
        assert "#42" in result
        assert "open" in result
        assert "bug" in result
        assert "testuser" in result

    @patch("jarvis.tools.github._get_client")
    def test_read_issue_no_body(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        mock_issue = MagicMock()
        mock_issue.number = 1
        mock_issue.title = "Vazia"
        mock_issue.state = "open"
        mock_issue.body = None
        mock_issue.user.login = "user"
        mock_issue.labels = []

        gh.get_repo.return_value.get_issue.return_value = mock_issue

        result = github_read_issue.invoke({"repo": "viaiv/jarvis", "issue_number": 1})

        assert "(sem descricao)" in result
        assert "nenhuma" in result

    @patch("jarvis.tools.github._get_client")
    def test_read_issue_error(self, mock_get_client):
        mock_get_client.side_effect = RuntimeError("GITHUB_TOKEN nao configurado")

        result = github_read_issue.invoke({"repo": "viaiv/jarvis", "issue_number": 1})
        assert "GITHUB_TOKEN" in result


class TestGithubReadFile:
    @patch("jarvis.tools.github._get_client")
    def test_read_file_success(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        mock_contents = MagicMock()
        mock_contents.decoded_content = b"print('hello')"
        gh.get_repo.return_value.default_branch = "main"
        gh.get_repo.return_value.get_contents.return_value = mock_contents

        result = github_read_file.invoke({"repo": "viaiv/jarvis", "path": "main.py"})

        assert "print('hello')" in result
        assert "main.py" in result

    @patch("jarvis.tools.github._get_client")
    def test_read_file_is_directory(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        gh.get_repo.return_value.default_branch = "main"
        gh.get_repo.return_value.get_contents.return_value = [MagicMock(), MagicMock()]

        result = github_read_file.invoke({"repo": "viaiv/jarvis", "path": "src"})
        assert "diretorio" in result

    @patch("jarvis.tools.github._get_client")
    def test_read_file_truncation(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        mock_contents = MagicMock()
        mock_contents.decoded_content = b"x" * 20000
        gh.get_repo.return_value.default_branch = "main"
        gh.get_repo.return_value.get_contents.return_value = mock_contents

        result = github_read_file.invoke({"repo": "viaiv/jarvis", "path": "big.py"})
        assert "truncado" in result


class TestGithubListFiles:
    @patch("jarvis.tools.github._get_client")
    def test_list_files_success(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        file1 = MagicMock()
        file1.name = "main.py"
        file1.path = "src/main.py"
        file1.type = "file"
        file1.size = 1024

        dir1 = MagicMock()
        dir1.name = "tests"
        dir1.path = "tests"
        dir1.type = "dir"

        gh.get_repo.return_value.default_branch = "main"
        gh.get_repo.return_value.get_contents.return_value = [file1, dir1]

        result = github_list_files.invoke({"repo": "viaiv/jarvis", "path": "."})

        assert "tests" in result
        assert "main.py" in result
        assert "2 itens" in result


class TestGithubCommentIssue:
    @patch("jarvis.tools.github._get_client")
    def test_comment_success(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        mock_comment = MagicMock()
        mock_comment.id = 999
        gh.get_repo.return_value.get_issue.return_value.create_comment.return_value = mock_comment

        result = github_comment_issue.invoke({
            "repo": "viaiv/jarvis",
            "issue_number": 42,
            "body": "Estou analisando esta issue.",
        })

        assert "Comentario criado" in result
        assert "#42" in result

    def test_comment_empty_body(self):
        result = github_comment_issue.invoke({
            "repo": "viaiv/jarvis",
            "issue_number": 1,
            "body": "  ",
        })
        assert "vazio" in result


class TestGithubCreateBranch:
    @patch("jarvis.tools.github._get_client")
    def test_create_branch_success(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        repo = gh.get_repo.return_value
        repo.default_branch = "main"
        repo.get_git_ref.return_value.object.sha = "abc12345deadbeef"

        result = github_create_branch.invoke({
            "repo": "viaiv/jarvis",
            "branch": "fix/42",
        })

        assert "fix/42" in result
        assert "main" in result
        repo.create_git_ref.assert_called_once()

    def test_create_branch_empty_name(self):
        result = github_create_branch.invoke({
            "repo": "viaiv/jarvis",
            "branch": "  ",
        })
        assert "vazio" in result


class TestGithubCreateOrUpdateFile:
    @patch("jarvis.tools.github._get_client")
    def test_create_new_file(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        repo = gh.get_repo.return_value
        repo.get_contents.side_effect = Exception("Not found")

        mock_commit = MagicMock()
        mock_commit.sha = "abc12345"
        repo.create_file.return_value = {"commit": mock_commit}

        result = github_create_or_update_file.invoke({
            "repo": "viaiv/jarvis",
            "path": "new_file.py",
            "message": "Add new file",
            "content": "print('hello')",
            "branch": "fix/42",
        })

        assert "criado" in result
        assert "new_file.py" in result

    @patch("jarvis.tools.github._get_client")
    def test_update_existing_file(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        repo = gh.get_repo.return_value
        existing = MagicMock()
        existing.sha = "old_sha"
        repo.get_contents.return_value = existing

        mock_commit = MagicMock()
        mock_commit.sha = "new12345"
        repo.update_file.return_value = {"commit": mock_commit}

        result = github_create_or_update_file.invoke({
            "repo": "viaiv/jarvis",
            "path": "existing.py",
            "message": "Update file",
            "content": "updated content",
            "branch": "fix/42",
        })

        assert "atualizado" in result

    def test_create_file_empty_branch(self):
        result = github_create_or_update_file.invoke({
            "repo": "viaiv/jarvis",
            "path": "file.py",
            "message": "msg",
            "content": "x",
            "branch": "",
        })
        assert "obrigatoria" in result


class TestGithubCreatePr:
    @patch("jarvis.tools.github._get_client")
    def test_create_pr_success(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        repo = gh.get_repo.return_value
        repo.default_branch = "main"

        mock_pr = MagicMock()
        mock_pr.number = 10
        mock_pr.title = "Fix login bug"
        mock_pr.html_url = "https://github.com/viaiv/jarvis/pull/10"
        repo.create_pull.return_value = mock_pr

        result = github_create_pr.invoke({
            "repo": "viaiv/jarvis",
            "title": "Fix login bug",
            "body": "Corrige o bug de login",
            "head": "fix/42",
        })

        assert "#10" in result
        assert "draft" in result
        assert "fix/42" in result
        repo.create_pull.assert_called_once_with(
            title="Fix login bug",
            body="Corrige o bug de login",
            head="fix/42",
            base="main",
            draft=True,
        )

    def test_create_pr_empty_title(self):
        result = github_create_pr.invoke({
            "repo": "viaiv/jarvis",
            "title": "",
            "body": "desc",
            "head": "fix/1",
        })
        assert "vazio" in result


class TestGithubAddLabel:
    @patch("jarvis.tools.github._get_client")
    def test_add_label_success(self, mock_get_client):
        gh = _mock_github()
        mock_get_client.return_value = gh

        result = github_add_label.invoke({
            "repo": "viaiv/jarvis",
            "issue_number": 42,
            "label": "bug",
        })

        assert "bug" in result
        assert "#42" in result

    def test_add_label_empty(self):
        result = github_add_label.invoke({
            "repo": "viaiv/jarvis",
            "issue_number": 1,
            "label": "",
        })
        assert "vazio" in result
