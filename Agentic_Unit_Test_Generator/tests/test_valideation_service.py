"""
Tests for NIC_SecEng_Task.valideation_service.ValidationService

Note: the module file lives at NIC_SecEng_Task/valideation_service.py (per task),
but the class also exists conceptually in user_management/validation_service.py.
We import via the module import path specified in the task instructions.
"""
import pytest

from NIC_SecEng_Task.valideation_service import ValidationService


@pytest.fixture
def service():
    return ValidationService()


# ---------------------------------------------------------------------------
# vulnerable_redirect: functional behavior / documents the known vulnerability
# ---------------------------------------------------------------------------

def test_vulnerable_redirect_returns_formatted_string_for_normal_url(service):
    """Verifies basic functional behavior: returns a formatted redirect string for a normal URL."""
    result = service.vulnerable_redirect("https://internalcompany.com/home")
    assert result == "Redirecting to https://internalcompany.com/home"


def test_vulnerable_redirect_documents_missing_validation_for_malicious_url(service):
    """Documents that vulnerable_redirect performs NO domain validation and blindly echoes an external malicious URL (known vulnerability, not a pass/fail security gate)."""
    malicious_url = "https://evil.com/phish"
    result = service.vulnerable_redirect(malicious_url)
    # This function is explicitly the "unhandled" vulnerability path in this module;
    # we assert its documented insecure behavior to characterize the flaw for detection tooling.
    assert malicious_url in result


def test_vulnerable_redirect_does_not_sanitize_javascript_scheme(service):
    """Documents that vulnerable_redirect does not block dangerous javascript: scheme payloads."""
    payload = "javascript:alert(1)"
    result = service.vulnerable_redirect(payload)
    assert payload in result


# ---------------------------------------------------------------------------
# secure_redirect: functional behavior for allowed domains
# ---------------------------------------------------------------------------

def test_secure_redirect_allows_root_internal_domain(service):
    """Verifies that a direct internalcompany.com URL with trailing slash is allowed."""
    url = "https://internalcompany.com/dashboard"
    result = service.secure_redirect(url)
    assert result == f"Redirecting to {url}"


def test_secure_redirect_allows_subdomain_of_internal_domain(service):
    """Verifies that a valid subdomain of internalcompany.com is allowed."""
    url = "https://app.internalcompany.com/login"
    result = service.secure_redirect(url)
    assert result == f"Redirecting to {url}"


# ---------------------------------------------------------------------------
# secure_redirect: vulnerability / bypass prevention tests
# ---------------------------------------------------------------------------

def test_secure_redirect_blocks_external_malicious_domain(service):
    """Ensures a fully external malicious domain is rejected with a ValueError (fail-safe outcome)."""
    with pytest.raises(ValueError):
        service.secure_redirect("https://evil.com/phish")


def test_secure_redirect_blocks_prefix_spoofing_without_dot_separator(service):
    """Ensures a domain that merely contains 'internalcompany.com' as a substring without a proper subdomain dot is rejected."""
    with pytest.raises(ValueError):
        service.secure_redirect("https://evilinternalcompany.com/attack")


def test_secure_redirect_blocks_suffix_domain_spoofing(service):
    """Ensures an attacker-controlled domain appended after internalcompany.com (e.g. internalcompany.com.evil.com) is rejected."""
    with pytest.raises(ValueError):
        service.secure_redirect("https://internalcompany.com.evil.com/steal")


def test_secure_redirect_blocks_missing_trailing_slash(service):
    """Ensures a URL missing the required trailing slash after the domain is rejected due to strict regex matching."""
    with pytest.raises(ValueError):
        service.secure_redirect("https://internalcompany.com")


def test_secure_redirect_blocks_non_https_scheme(service):
    """Ensures a plain http (non-https) scheme to the internal domain is rejected."""
    with pytest.raises(ValueError):
        service.secure_redirect("http://internalcompany.com/dashboard")


def test_secure_redirect_blocks_userinfo_injection_bypass(service):
    """Ensures an attacker cannot bypass validation by embedding userinfo/host confusion in the URL."""
    with pytest.raises(ValueError):
        service.secure_redirect("https://internalcompany.com@evil.com/")


def test_secure_redirect_blocks_case_variation_domain(service):
    """Ensures uppercase variations of the trusted domain are rejected since the regex is case-sensitive."""
    with pytest.raises(ValueError):
        service.secure_redirect("https://INTERNALCOMPANY.COM/dashboard")


def test_secure_redirect_blocks_embedded_redirect_query_param_attack(service):
    """Ensures a malicious host cannot be smuggled via a redirect-like query string appended after an evil host."""
    with pytest.raises(ValueError):
        service.secure_redirect("https://evil.com/redirect?next=https://internalcompany.com/")


def test_secure_redirect_blocks_empty_string(service):
    """Ensures an empty string input is rejected rather than silently redirecting."""
    with pytest.raises(ValueError):
        service.secure_redirect("")


def test_secure_redirect_blocks_javascript_scheme(service):
    """Ensures a javascript: scheme payload is rejected by the domain allow-list regex."""
    with pytest.raises(ValueError):
        service.secure_redirect("javascript:alert(document.domain)")


def test_secure_redirect_error_message_content(service):
    """Verifies that the raised ValueError contains a clear security violation message."""
    with pytest.raises(ValueError, match="Security Violation"):
        service.secure_redirect("https://malicious-site.net/")


def test_secure_redirect_raises_typeerror_for_non_string_input(service):
    """Ensures non-string input (e.g. integer) does not silently pass validation and raises a TypeError instead of being processed unsafely."""
    with pytest.raises(TypeError):
        service.secure_redirect(12345)


def test_secure_redirect_blocks_none_input(service):
    """Ensures None input raises a TypeError rather than being coerced into a valid redirect."""
    with pytest.raises(TypeError):
        service.secure_redirect(None)
