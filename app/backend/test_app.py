#!/usr/bin/env python3
"""
Test script to check FastAPI app creation
"""
import sys
import os
from pathlib import Path

# Add project root to Python path for proper imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

print('Testing FastAPI app creation...')
try:
    from fastapi import FastAPI
    from app.backend.core.config import get_settings

    app = FastAPI()
    settings = get_settings()
    print(f'✅ FastAPI app created successfully')
    print(f'✅ Settings: {settings.HOST}:{settings.PORT}')

    # Test import of routes
    from app.backend.api.v1.routes import health
    app.include_router(health.router)
    print('✅ Health router imported successfully')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()

