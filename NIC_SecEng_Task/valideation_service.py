# NIC_SecEng_Task/user_management/validation_service.py
import re

class ValidationService:
    """
    Scenario 3 Capacity Test: Evaluates if the Agent correctly differentiates 
    between handled and unhandled security vulnerabilities.
    """

    def vulnerable_redirect(self, target_url: str) -> str:
        """
        VULNERABILITY: Unvalidated URL Redirection.
        The agent's test case MUST pass a malicious URL (e.g., 'https://evil.com')
        and assert that it breaks/fails the security policy (fail-safe outcome).
        """
        # BAD: Blindly returns the URL without checking the domain boundary
        return f"Redirecting to {target_url}"


    def secure_redirect(self, target_url: str) -> str:
        """
        SECURE PATH: Properly Handled URL Redirection.
        The agent's test case MUST pass the same malicious URL but assert 
        that it throws a ValueError or returns a safe fallback.
        """
        # GOOD: Explicitly restricts redirection to internal corporate domains
        allowed_domain_regex = r"^https://([a-zA-Z0-9-]+\.)?internalcompany\.com/"
        
        if not re.match(allowed_domain_regex, target_url):
            raise ValueError("Security Violation: External redirection is strictly prohibited.")
            
        return f"Redirecting to {target_url}"