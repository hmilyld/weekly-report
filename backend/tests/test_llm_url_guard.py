"""LLM URL guard: loopback allowed, private/internal ranges blocked after DNS."""

import socket

import pytest

from app import llm_client


def _fake_addrinfo(ip):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 80))]


def _patch_dns(monkeypatch, ip):
    """Make every non-loopback hostname resolve to the given address."""
    original = socket.getaddrinfo

    def fake(host, port, *args, **kwargs):
        if host in ("localhost", "127.0.0.1", "::1"):
            return original(host, port, *args, **kwargs)
        return _fake_addrinfo(ip)

    monkeypatch.setattr(socket, "getaddrinfo", fake)


class TestUrlValidation:
    def test_local_ollama_default_is_allowed(self):
        """The shipped default points at localhost; the guard must accept it."""
        llm_client._validate_llm_url("http://localhost:11434/v1/chat/completions")

    def test_loopback_literal_allowed(self):
        llm_client._validate_llm_url("http://127.0.0.1:11434/v1")

    def test_ipv6_loopback_allowed(self):
        llm_client._validate_llm_url("http://[::1]:11434/v1")

    def test_public_host_allowed(self, monkeypatch):
        _patch_dns(monkeypatch, "93.184.216.34")

        llm_client._validate_llm_url("https://api.example.com/v1/chat/completions")

    @pytest.mark.parametrize(
        "ip",
        ["10.0.0.5", "192.168.1.10", "172.20.3.4", "169.254.169.254", "0.0.0.0"],
    )
    def test_dns_name_pointing_internally_is_blocked(self, monkeypatch, ip):
        _patch_dns(monkeypatch, ip)

        with pytest.raises(ValueError, match="not allowed"):
            llm_client._validate_llm_url("http://internal.example.com/v1")

    def test_non_http_scheme_blocked(self):
        with pytest.raises(ValueError, match="scheme"):
            llm_client._validate_llm_url("file:///etc/passwd")

    def test_unresolvable_host_is_a_value_error(self, monkeypatch):
        def boom(*args, **kwargs):
            raise socket.gaierror("nope")

        monkeypatch.setattr(socket, "getaddrinfo", boom)

        with pytest.raises(ValueError, match="无法解析"):
            llm_client._validate_llm_url("http://does-not-exist.invalid/v1")


class TestPromptBuilding:
    def test_newlines_become_separators(self):
        prompt = llm_client._build_prompt("本周日报记录：", [("2026-11-17", "a\nb")])

        assert prompt == "本周日报记录：\n2026-11-17：a；b"

    def test_empty_entries_keep_header(self):
        assert llm_client._build_prompt("本月日报记录：", []) == "本月日报记录："
