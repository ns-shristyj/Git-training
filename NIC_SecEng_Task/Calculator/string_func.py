
def reverse_string(text: str) -> str:
    """Reverses the provided string text."""
    return text[::-1]

def capitalize_words(text: str) -> str:
    """Capitalizes 1st letter of every word in a string."""
    if not text:
        return ""
    return " ".join(word.capitalize() for word in text.split())

def truncate(text: str, max_length: int) -> str:
    """Truncates text to specified length and appends ellipses (...) if it exceeds it."""
    if max_length <= 0:
        raise ValueError("Maximum length must be a positive integer.")
        
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."    
