import os
import sys
import traceback
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from mangum import Mangum

# Add the project root to Python path for Vercel
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Check for required environment variables before importing app
missing_vars = []
if not os.getenv("DATABASE_URL"):
    missing_vars.append("DATABASE_URL")
if not os.getenv("SECRET_KEY"):
    missing_vars.append("SECRET_KEY")

if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    print(f"ERROR: {error_msg}", file=sys.stderr)
    print(f"ERROR: Please set these in Vercel project settings -> Environment Variables", file=sys.stderr)
    
    # Create a minimal FastAPI app that returns helpful error messages
    error_app = FastAPI(title="Configuration Error")
    
    @error_app.get("/{full_path:path}")
    @error_app.post("/{full_path:path}")
    @error_app.put("/{full_path:path}")
    @error_app.delete("/{full_path:path}")
    @error_app.patch("/{full_path:path}")
    def error_endpoint(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Configuration Error",
                "message": error_msg,
                "details": "Please set the required environment variables in Vercel project settings -> Environment Variables",
                "missing_variables": missing_vars,
                "path": f"/{full_path}"
            }
        )
    
    handler = Mangum(error_app, lifespan="off")
else:
    # Import and initialize app
    # If this fails, the error will be visible in Vercel function logs
    try:
        from app.main import app
        # Wrap FastAPI app with Mangum for Vercel serverless compatibility
        handler = Mangum(app, lifespan="off")
    except Exception as e:
        # Log detailed error for Vercel logs
        error_details = traceback.format_exc()
        error_msg = str(e)
        print(f"CRITICAL: Failed to import app", file=sys.stderr)
        print(f"ERROR: {error_msg}", file=sys.stderr)
        print(f"TRACEBACK:\n{error_details}", file=sys.stderr)
        
        # Create error app that shows the actual error
        error_app = FastAPI(title="Initialization Error")
        
        @error_app.get("/{full_path:path}")
        @error_app.post("/{full_path:path}")
        @error_app.put("/{full_path:path}")
        @error_app.delete("/{full_path:path}")
        @error_app.patch("/{full_path:path}")
        def error_endpoint(full_path: str):
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Application Initialization Error",
                    "message": error_msg,
                    "details": "Check Vercel function logs for full traceback.",
                    "path": f"/{full_path}"
                }
            )
        
        handler = Mangum(error_app, lifespan="off")

