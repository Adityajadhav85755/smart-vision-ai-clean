import json
from flask import Flask, request, jsonify
from werkzeug.wrappers import Response

app = Flask(__name__)

def handler(environ, start_response):
    """Vercel serverless handler"""
    with app.request_context(environ):
        try:
            # Your existing app logic here
            from app import app as main_app
            
            # Forward to main Flask app
            return main_app.wsgi_app(environ, start_response)
        except Exception as e:
            response = jsonify({'error': str(e)})
            start_response('500 Internal Server Error', [
                ('Content-Type', 'application/json'),
                ('Access-Control-Allow-Origin', '*')
            ])
            return [response.data]
