 import streamlit as st

st.title("🔒 Secret Password Strength Checker")
st.write("Type a password below to see how secure it is.")

user_password = st.text_input("Enter your password:", type="password")

if user_password:
    password_length = len(user_password)
    has_number = any(char.isdigit() for char in user_password)
    
    if password_length < 6:
        st.error("🔴 Weak Password! It must be at least 6 characters long.")
    elif password_length >= 6 and not has_number:
        st.warning("🟡 Medium Password! Try adding at least one number (0-9).")
    else:
        st.success("🟢 Strong Password! Your account is safe.")