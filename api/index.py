from mangum import Mangum
from app.main import app

# Wrap FastAPI app with Mangum for Vercel serverless compatibility
handler = Mangum(app, lifespan="off")

