name: Run Hello World

on:
  push:
    # Runs only when code is pushed or merged directly into the develop branch
    branches:
      - develop
  pull_request:
    # Runs only when a Pull Request is opened against the develop branch
    branches:
      - develop

jobs:
  execute-python:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Run Hello World Script
        run: python helloworld.py
