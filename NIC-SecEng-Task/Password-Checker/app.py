import streamlit as st
# We import your secret rules here!
from password_logic import check_password_strength

st.title("🔒 Secret Password Strength Checker")
st.write("Type a password below to see how secure it is.")

user_password = st.text_input("Enter your password:", type="password")

if user_password:
    # Use the logic function to get the result
    result = check_password_strength(user_password)
    
    if result == "Weak":
        st.error("🔴 Weak Password! It must be at least 6 characters long.")
    elif result == "Medium":
        st.warning("🟡 Medium Password! Try adding at least one number (0-9).")
    else:
        st.success("🟢 Strong Password! Your account is safe.")