#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define the directories or files to check
TARGET=${1:-"."}

echo "Running flake8 on $TARGET"

# Run flake8
flake8 $TARGET

# Exit with success message if no errors found
echo "flake8 checks passed successfully!"
