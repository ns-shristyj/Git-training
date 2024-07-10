# Project Emu: SBOM Manager

Project Emu is a Software Bill of Materials (SBOM) manager designed to streamline the process of managing and tracking software components in your projects.

---

## Table of Contents

1. [Setup](#setup)
2. [Usage](#usage)
3. [Destroying](#destroying)

---

## Setup

To set up Project Emu on your local machine, follow these steps:

1. Clone the repository to your local machine.
2. Navigate to the project directory.
3. Copy the `.env.example` file to `.env` and populate the values.
4. Ensure `Make`, `pip3`, `python3`, and `virtualenv` (PIP) are installed on your local machine.
5. Run `make` to initialize the virtual environment and database.

---

## Usage

1. Run `make run` to start the web server.
2. Navigate to http://127.0.0.1:5000.

   a. To navigate to the login screen, go to http://127.0.0.1:5000/login.

---

## Destroying

1. To destory the enviroment, run `make clean`.
2. Next, run `make` to rebuild the environment.


---

© Netskope, 2024. All rights reserved.
