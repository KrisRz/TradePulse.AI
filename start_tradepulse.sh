#!/bin/bash
# TradePulse.AI - Unified Professional Monitor Startup Script
# Simple wrapper to start the complete TradePulse.AI system

set -euo pipefail

cd "$(dirname "$0")"

echo "🚀 TradePulse.AI Unified Professional Monitor"
echo "=============================================="
echo ""
echo "Starting complete TradePulse.AI system with professional monitoring..."
echo "This will start and monitor:"
echo "  • DynamoDB Local (Port 8000)"
echo "  • Backend API (Port 9002)" 
echo "  • Frontend Dev Server (Port 4321)"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi

# Check if required Python packages are available
python3 -c "import aiohttp, psutil" 2>/dev/null || {
    echo "❌ Missing required Python packages"
    echo "💡 Install with: pip install aiohttp psutil python-dotenv"
    exit 1
}

# Start the unified monitor
exec python3 TRADEPULSE_UNIFIED_MONITOR.py
