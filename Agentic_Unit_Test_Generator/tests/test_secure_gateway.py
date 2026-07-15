# test_secure_gateway.py
"""
Pytest test suite for NIC_SecEng_Task/user_management/secure_gateway.py

These tests validate both the functional correctness of SecureGateway and
attempt to expose the path traversal / command injection vulnerabilities
described in the source. Where the implementation is genuinely insecure,
the assertions are written to expect the SECURE outcome (per instructions),
so a failing assertion here is a signal that the vulnerability boundary
was violated by the implementation under test.
"""
import os
import shlex
import subprocess

import pytest

from NIC_SecEng_Task.user_management.secure_gateway import SecureGateway


# ---------------------------------------------------------------------------
# Constructor / basic behavior
# ---------------------------------------------------------------------------

def test_init_default_base_dir_is_absolute():
    """The default base_directory should be normalized to an absolute path."""
    gateway = SecureGateway()
    assert os.path.isabs(gateway.base_dir)
    assert gateway.base_dir == os.path.abspath("/var/www/uploads")


def test_init_custom_base_dir_is_normalized(tmp_path):
    """A custom base_directory should be stored as its absolute, normalized form."""
    relative_style = str(tmp_path) + os.sep + "." + os.sep + "sub"
    gateway = SecureGateway(base_directory=relative_style)
    assert gateway.base_dir == os.path.abspath(relative_style)


# ---------------------------------------------------------------------------
# read_user_file: functional correctness
# ---------------------------------------------------------------------------

def test_read_user_file_reads_existing_file_within_base_dir(tmp_path):
    """A legitimate file located inside base_dir should be read back correctly."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    target = base_dir / "hello.txt"
    target.write_text("hello world")

    gateway = SecureGateway(base_directory=str(base_dir))
    content = gateway.read_user_file("hello.txt")
    assert content == "hello world"


def test_read_user_file_reads_nested_subdirectory_file(tmp_path):
    """A legitimate nested file path within base_dir should be readable."""
    base_dir = tmp_path / "uploads"
    subdir = base_dir / "sub"
    subdir.mkdir(parents=True)
    target = subdir / "nested.txt"
    target.write_text("nested content")

    gateway = SecureGateway(base_directory=str(base_dir))
    content = gateway.read_user_file(os.path.join("sub", "nested.txt"))
    assert content == "nested content"


def test_read_user_file_missing_file_raises_file_not_found(tmp_path):
    """Requesting a nonexistent file should raise FileNotFoundError, not silently succeed."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    gateway = SecureGateway(base_directory=str(base_dir))

    with pytest.raises(FileNotFoundError):
        gateway.read_user_file("does_not_exist.txt")


# ---------------------------------------------------------------------------
# read_user_file: path traversal vulnerability boundary
# ---------------------------------------------------------------------------

def test_read_user_file_blocks_relative_directory_traversal(tmp_path):
    """A '../' traversal payload must not be able to read a file outside base_dir."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("TOP-SECRET-DATA")

    gateway = SecureGateway(base_directory=str(base_dir))
    traversal_payload = os.path.join("..", "secret.txt")

    try:
        content = gateway.read_user_file(traversal_payload)
    except (FileNotFoundError, ValueError, PermissionError):
        # Safely handled: traversal was blocked / rejected.
        return

    # If no exception was raised, the resolved path must still be confined to base_dir,
    # and the secret content must not have leaked.
    resolved = os.path.abspath(os.path.join(gateway.base_dir, traversal_payload))
    assert resolved.startswith(gateway.base_dir + os.sep), (
        "Path traversal payload escaped the sandboxed base directory"
    )
    assert "TOP-SECRET-DATA" not in content


def test_read_user_file_blocks_deep_relative_traversal(tmp_path):
    """A multi-level '../../' traversal payload attempting to reach system files must be blocked."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    gateway = SecureGateway(base_directory=str(base_dir))
    payload = "../" * 6 + "etc/passwd"

    try:
        gateway.read_user_file(payload)
    except (FileNotFoundError, ValueError, PermissionError):
        return

    resolved = os.path.abspath(os.path.join(gateway.base_dir, payload))
    assert resolved.startswith(gateway.base_dir + os.sep), (
        "Deep traversal payload escaped the sandboxed base directory"
    )


def test_read_user_file_blocks_absolute_path_override(tmp_path):
    """An absolute path input must not override the sandboxed base_dir via os.path.join semantics."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    gateway = SecureGateway(base_directory=str(base_dir))
    malicious_absolute_path = "/etc/passwd"

    try:
        gateway.read_user_file(malicious_absolute_path)
    except (FileNotFoundError, ValueError, PermissionError):
        return

    joined = os.path.join(gateway.base_dir, malicious_absolute_path)
    assert joined.startswith(gateway.base_dir), (
        "Absolute path input escaped the sandbox because os.path.join discarded base_dir"
    )


def test_read_user_file_rejects_embedded_null_byte(tmp_path):
    """A path containing an embedded null byte should be safely rejected, not cause undefined behavior."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    gateway = SecureGateway(base_directory=str(base_dir))
    payload = "hello.txt\x00.jpg"

    with pytest.raises((FileNotFoundError, ValueError, PermissionError)):
        gateway.read_user_file(payload)


# ---------------------------------------------------------------------------
# execute_diagnostic_ping: functional correctness (subprocess mocked)
# ---------------------------------------------------------------------------

def test_execute_diagnostic_ping_empty_host_returns_message():
    """An empty host_ip should short-circuit and return a fixed message without invoking a subprocess."""
    gateway = SecureGateway()
    result = gateway.execute_diagnostic_ping("")
    assert result == "No host specified"


def test_execute_diagnostic_ping_success_returns_subprocess_output(monkeypatch):
    """A successful ping should return exactly the subprocess output for a valid host."""
    def fake_check_output(command, shell=True, stderr=None, text=None):
        return "PING 127.0.0.1: 1 packets transmitted, 1 received"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    gateway = SecureGateway()
    result = gateway.execute_diagnostic_ping("127.0.0.1")
    assert "1 packets transmitted" in result


def test_execute_diagnostic_ping_failure_returns_error_message(monkeypatch):
    """A CalledProcessError during ping should be caught and reported in a formatted failure message."""
    def fake_check_output(command, shell=True, stderr=None, text=None):
        raise subprocess.CalledProcessError(returncode=1, cmd=command, output="unreachable host")

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    gateway = SecureGateway()
    result = gateway.execute_diagnostic_ping("10.0.0.999")
    assert result.startswith("Ping failed:")
    assert "unreachable host" in result


# ---------------------------------------------------------------------------
# execute_diagnostic_ping: command injection vulnerability boundary
# ---------------------------------------------------------------------------

def test_execute_diagnostic_ping_blocks_semicolon_command_chaining(monkeypatch):
    """A ';'-chained shell command injected via host_ip must not reach the shell unsanitized."""
    captured = {}

    def fake_check_output(command, shell=True, stderr=None, text=None):
        captured["command"] = command
        return "safe output"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    gateway = SecureGateway()
    malicious_host = "127.0.0.1; rm -rf /"

    gateway.execute_diagnostic_ping(malicious_host)

    # Secure handling requires the raw payload to be quoted/escaped or rejected entirely,
    # not concatenated verbatim into a shell=True command string.
    raw_injection_present = malicious_host in captured["command"]
    properly_quoted = shlex.quote(malicious_host) in captured["command"]
    assert not raw_injection_present or properly_quoted, (
        "Unsanitized shell metacharacters from host_ip were passed directly to the shell command"
    )


def test_execute_diagnostic_ping_blocks_backtick_command_substitution(monkeypatch):
    """A backtick command-substitution payload in host_ip must not be executed unsanitized."""
    captured = {}

    def fake_check_output(command, shell=True, stderr=None, text=None):
        captured["command"] = command
        return "safe output"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    gateway = SecureGateway()
    malicious_host = "`whoami`"

    gateway.execute_diagnostic_ping(malicious_host)

    raw_injection_present = malicious_host in captured["command"]
    properly_quoted = shlex.quote(malicious_host) in captured["command"]
    assert not raw_injection_present or properly_quoted, (
        "Backtick command substitution payload was passed directly to the shell command"
    )


def test_execute_diagnostic_ping_blocks_pipe_injection(monkeypatch):
    """A pipe ('|') injection payload in host_ip must not be forwarded unsanitized to the shell."""
    captured = {}

    def fake_check_output(command, shell=True, stderr=None, text=None):
        captured["command"] = command
        return "safe output"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    gateway = SecureGateway()
    malicious_host = "127.0.0.1 | cat /etc/passwd"

    gateway.execute_diagnostic_ping(malicious_host)

    raw_injection_present = malicious_host in captured["command"]
    properly_quoted = shlex.quote(malicious_host) in captured["command"]
    assert not raw_injection_present or properly_quoted, (
        "Pipe-based command injection payload was passed directly to the shell command"
    )
