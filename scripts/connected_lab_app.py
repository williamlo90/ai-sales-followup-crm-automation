"""Lab instrumentation around the actual application factory; no business override."""
import json,os
from pathlib import Path
from starlette.responses import Response
from backend.app import from_environment

def factory():
    app=from_environment()
    @app.middleware('http')
    async def capture(request,call_next):
        response=await call_next(request)
        if request.url.path=='/v1/skills/extract_commitments':
            body=b''.join([part async for part in response.body_iterator])
            Path(os.environ['SALES_LAB_EXTRACTION_OUTPUT']).write_bytes(body)
            return Response(body,status_code=response.status_code,headers=dict(response.headers),media_type=response.media_type)
        return response
    return app
