# test_validation_service.py
import pytest

from NIC_SecEng_Task.valideation_service import ValidationService


@pytest.fixture
def service():
    return ValidationService()


class TestVulnerableRedirect:
    def test_returns_malicious_external_url_unvalidated(self, service):
        """Documents that vulnerable_redirect blindly accepts an external malicious URL (insecure baseline)."""
        malicious_url = "https://evil.com"
        result = service.vulnerable_redirect(malicious_url)
        assert result == f"Redirecting to {malicious_url}"

    def test_returns_internal_url_unchanged(self, service):
        """Verifies basic functionality: a legitimate internal URL is echoed back correctly."""
        url = "https://internalcompany.com/dashboard"
        result = service.vulnerable_redirect(url)
        assert result == f"Redirecting to {url}"

    def test_accepts_javascript_scheme_without_validation(self, service):
        """Shows vulnerable_redirect does not block dangerous non-http schemes like javascript:."""
        payload = "javascript:alert(1)"
        result = service.vulnerable_redirect(payload)
        assert result == f"Redirecting to {payload}"

    def test_accepts_empty_string(self, service):
        """Confirms vulnerable_redirect performs no input validation, even for empty input."""
        result = service.vulnerable_redirect("")
        assert result == "Redirecting to "


class TestSecureRedirectFunctionality:
    def test_allows_root_internal_domain(self, service):
        """Verifies secure_redirect allows a valid internalcompany.com URL with trailing path."""
        url = "https://internalcompany.com/home"
        result = service.secure_redirect(url)
        assert result == f"Redirecting to {url}"

    def test_allows_subdomain_of_internal_domain(self, service):
        """Verifies secure_redirect allows a valid subdomain of internalcompany.com."""
        url = "https://app.internalcompany.com/login"
        result = service.secure_redirect(url)
        assert result == f"Redirecting to {url}"


class TestSecureRedirectVulnerabilities:
    def test_blocks_external_malicious_domain(self, service):
        """Ensures secure_redirect raises ValueError for an unrelated external malicious domain."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("https://evil.com")

    def test_blocks_domain_suffix_spoofing(self, service):
        """Ensures secure_redirect rejects a lookalike domain that merely ends with internalcompany.com-like suffix."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("https://evilinternalcompany.com/")

    def test_blocks_subdomain_confusion_attack(self, service):
        """Ensures secure_redirect rejects a URL where internalcompany.com appears as a subdomain of an attacker domain."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("https://internalcompany.com.evil.com/")

    def test_blocks_userinfo_confusion_attack(self, service):
        """Ensures secure_redirect rejects a URL using userinfo trick to embed trusted domain before an evil host."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("https://internalcompany.com@evil.com/")

    def test_blocks_http_scheme_downgrade(self, service):
        """Ensures secure_redirect rejects non-https scheme even if domain matches, due to strict https requirement."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("http://internalcompany.com/")

    def test_blocks_missing_trailing_slash(self, service):
        """Ensures secure_redirect rejects a URL missing the required trailing slash after the domain."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("https://internalcompany.com")

    def test_blocks_javascript_scheme_payload(self, service):
        """Ensures secure_redirect rejects a javascript: URI injection attempt."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("javascript:alert(document.cookie)")

    def test_blocks_empty_string(self, service):
        """Ensures secure_redirect rejects an empty string input as it does not match the allowed pattern."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("")

    def test_blocks_case_variation_domain(self, service):
        """Ensures secure_redirect rejects a domain that uses uppercase to potentially bypass case-sensitive matching."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("https://INTERNALCOMPANY.COM/")

    def test_blocks_path_traversal_style_payload(self, service):
        """Ensures secure_redirect rejects a payload attempting path traversal combined with external domain."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("https://evil.com/../internalcompany.com/")

    def test_blocks_malformed_extra_at_symbol_bypass(self, service):
        """Ensures secure_redirect rejects a URL leveraging multiple '@' symbols to confuse host parsing."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("https://attacker.com@internalcompany.com@evil.com/")

    def test_blocks_null_byte_injection(self, service):
        """Ensures secure_redirect rejects a URL containing a null byte injection attempt."""
        with pytest.raises(ValueError, match="Security Violation"):
            service.secure_redirect("https://internalcompany.com/\x00.evil.com")
