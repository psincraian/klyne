"""Custom StaticFiles handler with long-term caching for static assets."""

from fastapi.staticfiles import StaticFiles
from starlette.responses import Response as StarletteResponse


class CachedStaticFiles(StaticFiles):
    """StaticFiles with long-term caching headers for static assets."""

    def __init__(self, *args, max_age: int = 31536000, **kwargs):
        """
        Initialize CachedStaticFiles.
        
        Args:
            max_age: Cache max-age in seconds (default: 1 year = 31536000)
        """
        super().__init__(*args, **kwargs)
        self.max_age = max_age

    async def get_response(self, path: str, scope: dict) -> StarletteResponse:
        """Override to add cache headers to static file responses."""
        response = await super().get_response(path, scope)
        
        # Only add cache headers for successful responses
        if response.status_code == 200:
            # Set long-term caching headers
            response.headers["Cache-Control"] = f"public, max-age={self.max_age}, immutable"
            response.headers["Expires"] = self._get_expires_header()
            
            # Add ETag support for better caching
            if "etag" not in response.headers:
                response.headers["ETag"] = f'"{hash(path)}"'
        
        return response

    def _get_expires_header(self) -> str:
        """Generate Expires header value for 1 year from now."""
        from datetime import datetime, timezone, timedelta
        
        expires_date = datetime.now(timezone.utc) + timedelta(seconds=self.max_age)
        return expires_date.strftime("%a, %d %b %Y %H:%M:%S GMT")