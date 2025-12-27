#!/bin/bash

# Complete setup and demo runner for Phase 1 & Phase 2
# Run this script to validate everything works

set -e  # Exit on error

echo "========================================================================"
echo "SENTINEL FRAMEWORK - PHASE 1 & PHASE 2 VALIDATION"
echo "========================================================================"
echo ""

# Step 1: Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "   cd /home/karteek/Documents/Cloud_Workspace/ai_agent_security"
    exit 1
fi

echo "✓ In correct directory"
echo ""

# Step 2: Check for virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi
echo ""

# Step 3: Activate virtual environment and install dependencies
echo "Installing dependencies..."
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip > /dev/null 2>&1

# Install package in editable mode
pip install -e . > /dev/null 2>&1
echo "✓ Sentinel package installed"

# Install required dependencies
pip install pydantic langgraph > /dev/null 2>&1
echo "✓ Dependencies installed"
echo ""

# Step 4: Run Phase 1 Demo
echo "========================================================================"
echo "RUNNING PHASE 1 DEMO (Risk Scoring & Context Propagation)"
echo "========================================================================"
echo ""

PYTHONPATH=/home/karteek/Documents/Cloud_Workspace/ai_agent_security python3 examples/demo_phase1.py

echo ""
echo "========================================================================"
echo "RUNNING PHASE 2 DEMO (Shadow Agent Integration)"
echo "========================================================================"
echo ""

PYTHONPATH=/home/karteek/Documents/Cloud_Workspace/ai_agent_security python3 examples/demo_phase2.py

echo ""
echo "========================================================================"
echo "✅ ALL DEMONSTRATIONS COMPLETE"
echo "========================================================================"
echo ""
echo "Both Phase 1 and Phase 2 are working correctly!"
echo ""
echo "Next steps:"
echo "  1. Review the output above to see all features in action"
echo "  2. Try the examples in examples/ directory"
echo "  3. Run tests: pytest -v (after installing pytest)"
echo "  4. Deploy to production!"
echo ""
