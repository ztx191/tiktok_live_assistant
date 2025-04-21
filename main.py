import os
import logging
import uvicorn
from fastapi import FastAPI

from src.router import assistant_router, advisor_route, kb_route, get_news

# 配置日志
from datetime import datetime

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Generate log filename with current date
log_filename = f"logs/{datetime.now().strftime('%Y-%m-%d')}.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set log level to INFO and above
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Set log format
    handlers=[
        logging.StreamHandler(),  # Add StreamHandler to output logs to terminal
        logging.FileHandler(log_filename, encoding='utf-8')  # Add FileHandler to output logs to file
    ]
)


logger = logging.getLogger(__name__)

app = FastAPI(root_path="/tiktok-api")

app.include_router(assistant_router.router)
app.include_router(advisor_route.router)
app.include_router(kb_route.router)
app.include_router(get_news.router)

@app.get("/")
async def root():
    return "api-server is running."

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=1121)