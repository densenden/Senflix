from app import app

# Handler para Vercel
def handler(request, **kwargs):
    """
    Handler para Vercel Serverless Functions
    """
    return app(request.environ, request.start_response) 