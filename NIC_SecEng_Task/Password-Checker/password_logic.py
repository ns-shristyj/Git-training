def check_password_strength(password):
    """This function takes a password text and returns how strong it is."""
    if len(password) < 6:
        return "Weak"
    elif not any(char.isdigit() for char in password):
        return "Medium"
    else:
        return "Strong"