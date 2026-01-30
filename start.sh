#!/bin/bash
# Startup script for running both Gradio and API services

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default mode
MODE=${1:-"both"}

case "$MODE" in
    "api")
        echo "Starting FastAPI service..."
        python main.py
        ;;
    "gradio")
        echo "Starting Gradio service..."
        python app.py
        ;;
    "both")
        echo "Starting both services..."
        python main.py &
        API_PID=$!
        python app.py &
        GRADIO_PID=$!

        # Wait for both processes
        wait $API_PID
        wait $GRADIO_PID
        ;;
    *)
        echo "Usage: $0 {api|gradio|both}"
        exit 1
        ;;
esac
