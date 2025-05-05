from app import app

# Vercel serverless handler
def handler(request, **kwargs):
    """Handle Vercel serverless requests by proxying to Flask app"""
    return app(request.environ, request.start_response)

if __name__ == "__main__":
    app.run() 