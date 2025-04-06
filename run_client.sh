#!/bin/bash
source venv/bin/activate
cd "$(dirname "${BASH_SOURCE[0]}")/client_files" && python client.py
