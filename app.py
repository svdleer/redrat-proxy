import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the Flask app with detailed error handling
print("🔍 Root app.py: Starting Flask app import...")
try:
    print("🔍 Root app.py: Trying primary import...")
    from app.app import app
    print("✅ Root app.py: Primary import successful")
except ImportError as e:
    print(f"⚠️  Root app.py: Primary import failed: {e}")
    try:
        print("🔍 Root app.py: Trying alternative import...")
        import app.app as flask_app_module
        app = flask_app_module.app
        print("✅ Root app.py: Alternative import successful")
    except Exception as e2:
        print(f"❌ Root app.py: All imports failed: {e2}")
        raise

# Verify the app object is available
print(f"✅ Root app.py: Flask app available: {app}")
print(f"✅ Root app.py: Flask app type: {type(app)}")

if __name__ == '__main__':
    # When running directly, use the development server
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting Flask server on {host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug)
