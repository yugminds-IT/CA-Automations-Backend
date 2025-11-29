import os
import sys
import traceback
from mangum import Mangum

# Add the project root to Python path for Vercel
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import and initialize app
# If this fails, the error will be visible in Vercel function logs
try:
    from app.main import app
except Exception as e:
    # Log detailed error for Vercel logs
    error_details = traceback.format_exc()
    print(f"CRITICAL: Failed to import app\n{error_details}", file=sys.stderr)
    raise  # Re-raise so Vercel shows the error

# Wrap FastAPI app with Mangum for Vercel serverless compatibility
handler = Mangum(app, lifespan="off")

