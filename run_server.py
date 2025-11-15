"""
Simple script to run the TASCO server
"""
import uvicorn
import os

if __name__ == "__main__":
    # Create models directory if it doesn't exist
    os.makedirs("models", exist_ok=True)
    
    # Run server
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False  # Disable reload for stability
    )

