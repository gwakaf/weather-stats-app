from flask import Flask
import os

def create_app():
    # Get the path to the web_interface directory
    # __file__ is in app/__init__.py
    # We need to go up one level to get to project root, then into web_interface
    project_root = os.path.dirname(os.path.dirname(__file__))
    web_interface_path = os.path.join(project_root, 'web_interface')
    
    app = Flask(__name__, 
               template_folder=os.path.join(web_interface_path, 'templates'),
               static_folder=os.path.join(web_interface_path, 'static'))
    
    # Import and register routes
    from .routes import register_routes
    register_routes(app)
    return app 