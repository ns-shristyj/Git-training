from password_logic import check_password_strength

def run_tests():
    print("Starting secret agent password tests... 🕵️‍♂️")
    
    # Test 1: Short password should be Weak
    assert check_password_strength("123") == "Weak"
    
    # Test 2: Long password with NO numbers should be Medium
    assert check_password_strength("abcdef") == "Medium"
    
    # Test 3: Long password WITH numbers should be Strong
    assert check_password_strength("secret123") == "Strong"
    
    print("All tests passed successfully! Your app brain works perfectly. 🎉")

if __name__ == "__main__":
    run_tests()