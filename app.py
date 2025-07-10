from app.app import app

# This file allows Gunicorn to import the app correctly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
