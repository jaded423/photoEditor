#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH"
    echo "Please install Python 3 or ensure it's in your PATH"
    exit 1
fi

# The Python file to run

PYTHON_FILE="combined_processor.py"

# Check if the Python file exists
if [ ! -f "$PYTHON_FILE" ]; then
    echo "Error: $PYTHON_FILE not found in the current directory"
    echo "Available Python files:"
    ls *.py 2>/dev/null || echo "No Python files found"
    exit 1
fi

echo "Running python3 combined_processor.py raw/"
echo "Working directory: $SCRIPT_DIR"
echo "----------------------------------------"

# Run the Python script with the raw directory
python3 combined_processor.py raw/

# Capture the exit code
EXIT_CODE=$?

echo "----------------------------------------"
if [ $EXIT_CODE -eq 0 ]; then
    echo "Script completed successfully"
else
    echo "Script exited with error code: $EXIT_CODE"
fi

# Keep terminal open so user can see output
echo "Press any key to continue..."
read -n 1 -s
