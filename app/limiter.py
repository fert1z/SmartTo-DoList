"""Rate limiting for Flask application using Flask-Limiter"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize limiter (to be attached to app in __init__.py)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
