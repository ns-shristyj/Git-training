import os
import requests
import sys
from dotenv import load_dotenv

load_dotenv()

githubToken = os.getenv("GITHUB_TOKEN") # Make sure to switch to service token if this gets pushed to prod
user = os.getenv("TARGET_USER")

if githubToken is None:
    print("Access token not found")
    sys.exit(1)

if user is None:
    print("Requires a valid user")
    sys.exit(1)
#user = input("Enter user: ") # Temp, replace with webhook input

def getUser(user):
    
    gDomain = "https://api.github.com/"
    endpoint = f"users/{user}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "Authorization": f"Bearer {githubToken}"
    }

    try:
        print(f"Fetching user account: {user}")

        response = requests.get(gDomain+endpoint, headers=headers, timeout=30)
        response.raise_for_status()
        userData = response.json()
        
        if userData["email"] is not None:
            return("User has public email")
        else:
            return("User email not found")


    except requests.exceptions.HTTPError as error:
        if error.response.status_code == 404:
            return(f"User {user} not found.")
        else:
            return(f"HTTP error occurred: {error}")
    except requests.exceptions.Timeout:
        return("The request timed out. Please try again later.")
    except requests.exceptions.RequestException as error:
        return(f"An error occurred: {error}")

if __name__ == "__main__":
    print(getUser(user))
