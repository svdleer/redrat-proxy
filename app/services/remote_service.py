import sys
import os

# Add the app directory to the path to import the database module
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

# Import the database connection from the app
try:
    # Try local import first (when running as a module)
    from app.mysql_db import db
except ImportError:
    # Fall back to relative import (when importing within the package)
    from ..mysql_db import db

# Import IRNetBox functionality
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from remoteservice_txt import import_remotes_from_irnetbox as import_irnetbox_func
except ImportError as e:
    print(f"Warning: Could not import IRNetBox functionality: {e}")
    # If import fails, define a placeholder function
    def import_irnetbox_func(filepath, user_id):
        raise Exception("IRNetBox import functionality not available")

def import_remotes_from_irnetbox(filepath, user_id):
    """Import remotes from an IRNetBox format file"""
    return import_irnetbox_func(filepath, user_id)

# Maintain compatibility for any code that might still reference XML functions
def import_remotes_from_xml(xml_path, user_id):
    """Legacy function - redirects to IRNetBox import with deprecation warning"""
    raise Exception("XML import is deprecated. Please use IRNetBox format files (.txt) instead.")

def parse_remotes_xml(xml_path):
    """Legacy function - raises deprecation error"""
    raise Exception("XML parsing is deprecated. Please use IRNetBox format files (.txt) instead.")
