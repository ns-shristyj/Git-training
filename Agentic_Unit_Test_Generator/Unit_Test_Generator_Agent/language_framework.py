"""Extension -> (language, framework) detection for the test generator agent."""
import os

EXTENSION_MAP = {
    ".py": ("python", "pytest"),
    ".java": ("java", "JUnit 5"),
    ".ts": ("typescript", "Jest"),
    ".tsx": ("typescript", "Jest"),
    ".js": ("javascript", "Jest"),
    ".jsx": ("javascript", "Jest"),
    ".go": ("go", "go test"),
}


def detect_language_framework(file_path: str, language_override: str = None, framework_override: str = None):
    if language_override and framework_override:
        return language_override, framework_override

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in EXTENSION_MAP:
        raise ValueError(f"Unrecognized file extension '{ext}' for '{file_path}' — no known language/framework mapping")

    detected_language, detected_framework = EXTENSION_MAP[ext]
    return language_override or detected_language, framework_override or detected_framework
