#!/bin/bash
set -e

echo "Running Verification Checks..."

# 1. Run Tests with pytest
echo "Running pytest..."
pytest

echo "Verification Successful!"
