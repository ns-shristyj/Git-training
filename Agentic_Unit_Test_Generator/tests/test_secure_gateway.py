# test_secure_gateway.py
import os
import subprocess

import pytest

import NIC_SecEng_Task.user_management.secure_gateway as sg_module
from NIC_SecEng_Task.user_management.secure_gateway import SecureGateway


# ---------------------------------------------------------------------------
# __init__ tests
# ---------------------------------------------------------------------------

def test_init_converts_relative_base_dir_to_absolute(tmp_path, monkeypatch):
    """base_dir should always be stored as an absolute path, even if a relative path is supplied."""
    monkeypatch.chdir(tmp_path)
    gateway = SecureGateway(base_directory="relative_uploads")
    assert os.path.isabs(gateway.base_dir)
    assert gateway.base_dir == os.path.abspath("relative_uploads")


# ---------------------------------------------------------------------------
# read_user_file tests
# ---------------------------------------------------------------------------

def test_read_user_file_reads_existing_file_successfully(tmp_path):
    """A legitimate file located inside base_dir should be read correctly."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    target_file = base_dir / "hello.txt"
    target_file.write_text("hello world")

    gateway = SecureGateway(base_directory=str(base_dir))
    content = gateway.read_user_file("hello.txt")

    assert content == "hello world"


def test_read_user_file_raises_for_nonexistent_file(tmp_path):
    """Requesting a file that does not exist inside base_dir should raise FileNotFoundError."""
    gateway = SecureGateway(base_directory=str(tmp_path))

    with pytest.raises(FileNotFoundError):
        gateway.read_user_file("does_not_exist.txt")


def test_read_user_file_blocks_relative_path_traversal_outside_base_dir(tmp_path):
    """Relative '../' traversal must not allow reading files outside base_dir."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    secret_file = secret_dir / "secret.txt"
    secret_file.write_text("TOP SECRET DATA")

    gateway = SecureGateway(base_directory=str(base_dir))
    traversal_path = "../secret/secret.txt"

    # A secure implementation must refuse to serve any file resolved outside base_dir.
    with pytest.raises((FileNotFoundError, PermissionError, ValueError)):
        gateway.read_user_file(traversal_path)


def test_read_user_file_blocks_absolute_path_override(tmp_path):
    """Supplying an absolute path (e.g. '/etc/passwd') must not override base_dir confinement."""
    gateway = SecureGateway(base_directory=str(tmp_path))

    # A secure implementation must reject absolute paths that escape base_dir,
    # rather than silently resolving to the raw absolute path.
    with pytest.raises((FileNotFoundError, PermissionError, ValueError)):
        gateway.read_user_file("/etc/passwd")


def test_read_user_file_rejects_null_byte_injection(tmp_path):
    """Embedded NUL bytes in the file path must not be usable to bypass path validation."""
    gateway = SecureGateway(base_directory=str(tmp_path))

    with pytest.raises(ValueError):
        gateway.read_user_file("legit.txt\x00.jpg")


# ---------------------------------------------------------------------------
# execute_diagnostic_ping tests
# ---------------------------------------------------------------------------

def test_execute_diagnostic_ping_returns_no_host_message_for_empty_string():
    """An empty host_ip should short-circuit and never reach subprocess execution."""
    gateway = SecureGateway()
    result = gateway.execute_diagnostic_ping("")
    assert result == "No host specified"


def test_execute_diagnostic_ping_success_with_legit_host(monkeypatch):
    """A well-formed, legitimate host should produce the expected ping output without injection."""
    captured = {}

    def fake_check_output(command, shell=True, stderr=None, text=None):
        captured["command"] = command
        return "1 packets transmitted, 1 received"

    monkeypatch.setattr(sg_module.subprocess, "check_output", fake_check_output)

    gateway = SecureGateway()
    result = gateway.execute_diagnostic_ping("127.0.0.1")

    assert result == "1 packets transmitted, 1 received"
    assert "127.0.0.1" in captured["command"]


def test_execute_diagnostic_ping_handles_called_process_error(monkeypatch):
    """When ping fails, the function should catch CalledProcessError and return a failure message."""
    def fake_check_output(command, shell=True, stderr=None, text=None):
        raise subprocess.CalledProcessError(returncode=1, cmd=command, output="unreachable")

    monkeypatch.setattr(sg_module.subprocess, "check_output", fake_check_output)

    gateway = SecureGateway()
    result = gateway.execute_diagnostic_ping("10.0.0.1")

    assert result.startswith("Ping failed:")
    assert "unreachable" in result


def test_execute_diagnostic_ping_rejects_semicolon_command_injection(monkeypatch):
    """A ';' command chaining payload must be sanitized/rejected before shell execution."""
    captured = {}

    def fake_check_output(command, shell=True, stderr=None, text=None):
        captured["command"] = command
        return "output"

    monkeypatch.setattr(sg_module.subprocess, "check_output", fake_check_output)

    gateway = SecureGateway()
    malicious_payload = "127.0.0.1; rm -rf /"
    gateway.execute_diagnostic_ping(malicious_payload)

    # A secure implementation must never forward the raw injection separator to the shell.
    assert ";" not in captured["command"], "Command injection separator ';' was not sanitized"


def test_execute_diagnostic_ping_rejects_backtick_command_injection(monkeypatch):
    """A backtick command-substitution payload must be sanitized/rejected before shell execution."""
    captured = {}

    def fake_check_output(command, shell=True, stderr=None, text=None):
        captured["command"] = command
        return "output"

    monkeypatch.setattr(sg_module.subprocess, "check_output", fake_check_output)

    gateway = SecureGateway()
    malicious_payload = "127.0.0.1`whoami`"
    gateway.execute_diagnostic_ping(malicious_payload)

    assert "`" not in captured["command"], "Backtick command substitution was not sanitized"


def test_execute_diagnostic_ping_rejects_dollar_subshell_injection(monkeypatch):
    """A $() subshell substitution payload must be sanitized/rejected before shell execution."""
    captured = {}

    def fake_check_output(command, shell=True, stderr=None, text=None):
        captured["command"] = command
        return "output"

    monkeypatch.setattr(sg_module.subprocess, "check_output", fake_check_output)

    gateway = SecureGateway()
    malicious_payload = "127.0.0.1$(id)"
    gateway.execute_diagnostic_ping(malicious_payload)

    assert "$(" not in captured["command"], "Dollar-subshell substitution was not sanitized"


def test_execute_diagnostic_ping_rejects_pipe_injection(monkeypatch):
    """A pipe '|' payload chaining an extra command must be sanitized/rejected before shell execution."""
    captured = {}

    def fake_check_output(command, shell=True, stderr=None, text=None):
        captured["command"] = command
        return "output"

    monkeypatch.setattr(sg_module.subprocess, "check_output", fake_check_output)

    gateway = SecureGateway()
    malicious_payload = "127.0.0.1 | cat /etc/shadow"
    gateway.execute_diagnostic_ping(malicious_payload)

    assert "|" not in captured["command"], "Pipe injection payload was not sanitized"
