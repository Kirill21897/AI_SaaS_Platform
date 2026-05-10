import redis
from app.core.config import settings

# Use default redis host if running locally, or the docker service name if inside docker
# Since FastAPI runs locally in development, we use localhost:6379
redis_client = redis.Redis(
    host='localhost', 
    port=6379, 
    db=0, 
    decode_responses=True
)
