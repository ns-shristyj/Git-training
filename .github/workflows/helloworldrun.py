name: Run Hello World

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

jobs:
  execute-python:
    runs-on: ubuntu-latest

    steps:
      # Step 1: Check out the repository code
      - name: Checkout code
        uses: actions/checkout@v4

      # Step 2: Set up Python on the runner
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      # Step 3: Execute your specific script
      - name: Run Hello World Script
        run: python helloworld.py
