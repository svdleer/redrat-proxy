#!/usr/bin/env python3
"""
Advanced cleanup script for RedRat Proxy project.
This script identifies and removes unused files from the project.
"""

import os
import shutil
import argparse
import datetime

# Core project files/directories that should never be deleted
CORE_FILES = [
    'app.py',
    'docker-compose.yml',
    'Dockerfile',
    'requirements.txt',
    'mysql_schema.sql',
    'docker-entrypoint.sh',
    'README.md',
    '.gitignore',
    '.env',
    '.env.example',
]

CORE_DIRS = [
    'app',
    'apache',
    '.git',
]

# Key maintenance scripts to preserve
MAINTENANCE_SCRIPTS = [
    'reset_admin_password.py',  # Password reset utility
    'housekeeping.py',          # File cleanup utility
    'login_diagnostic.py',      # Login troubleshooting
    'convert_logo.py',          # Logo conversion utility
    'maintenance.bat',          # Main maintenance menu
    'cleanup.py',               # This script
]

def list_unused_scripts(directory):
    """List potentially unused script files in the directory"""
    unused_scripts = []
    all_files = os.listdir(directory)
    
    for filename in all_files:
        filepath = os.path.join(directory, filename)
        
        # Skip directories and core files
        if os.path.isdir(filepath) or filename in CORE_FILES or filename in MAINTENANCE_SCRIPTS:
            continue
            
        # Skip non-script files
        if not filename.endswith(('.py', '.sh', '.bat')):
            continue
            
        # Check if the file appears to be a utility script
        is_utility = any(name in filename.lower() for name in 
                         ['setup', 'init', 'build', 'reset', 'check', 'wait', 'make', 'test', 'run'])
                         
        if is_utility:
            unused_scripts.append(filename)
    
    return unused_scripts

def create_backup(directory, files_to_backup):
    """Create backup of files before deletion"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(directory, f"backup_{timestamp}")
    
    if not files_to_backup:
        return None
        
    os.makedirs(backup_dir)
    
    for filename in files_to_backup:
        source = os.path.join(directory, filename)
        destination = os.path.join(backup_dir, filename)
        shutil.copy2(source, destination)
    
    return backup_dir

def main():
    parser = argparse.ArgumentParser(description='RedRat Proxy cleanup utility')
    parser.add_argument('--dry-run', action='store_true', 
                      help='Show which files would be removed without actually deleting them')
    parser.add_argument('--no-backup', action='store_true',
                      help='Skip creating backups of files before deletion')
    args = parser.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=== RedRat Proxy Project Cleanup ===\n")
    
    # List of known unnecessary files
    known_unused = [
        'reset_admin.py',        # Redundant (use reset_admin_password.py)
        'check_db_health.py',    # Functionality now in login_diagnostic.py
        'build_css.bat',         # Empty/unused
        'build_css.sh',          # Empty/unused
        'init_db_manual.sh',     # Redundant with Docker setup
        'make_executable.sh',    # One-time utility
        'wait-for-it.sh',        # Superseded by Docker health checks
    ]
    
    # Get all potential unused scripts
    all_unused = list_unused_scripts(project_dir)
    
    # Filter to only show files that actually exist
    unused_files = [f for f in all_unused if os.path.exists(os.path.join(project_dir, f))]
    known_files = [f for f in known_unused if os.path.exists(os.path.join(project_dir, f))]
    
    # Show which files would be deleted
    if known_files:
        print("The following known unnecessary files were found:")
        for filename in known_files:
            print(f" - {filename}")
    else:
        print("No known unnecessary files found.")
        
    print("\nThe following additional scripts might be unnecessary:")
    if unused_files:
        for filename in unused_files:
            if filename not in known_files:
                print(f" - {filename}")
    else:
        print(" None")
    
    if args.dry_run:
        print("\nDry run completed. No files were deleted.")
        return
    
    # Confirm deletion
    if not known_files and not unused_files:
        print("\nNo files to delete.")
        return
        
    confirm = input("\nDelete known unnecessary files? (y/n): ")
    if confirm.lower() == 'y':
        # Create backup if requested
        if not args.no_backup:
            backup_dir = create_backup(project_dir, known_files)
            if backup_dir:
                print(f"\nBackup created in {backup_dir}")
        
        # Delete files
        for filename in known_files:
            filepath = os.path.join(project_dir, filename)
            os.remove(filepath)
            print(f"Deleted: {filename}")
    
    confirm = input("\nDelete additional potentially unused scripts? (y/n): ")
    if confirm.lower() == 'y':
        files_to_delete = [f for f in unused_files if f not in known_files]
        
        # Create backup if requested
        if not args.no_backup and files_to_delete:
            backup_dir = create_backup(project_dir, files_to_delete)
            if backup_dir:
                print(f"\nBackup created in {backup_dir}")
        
        # Delete files
        for filename in files_to_delete:
            filepath = os.path.join(project_dir, filename)
            os.remove(filepath)
            print(f"Deleted: {filename}")
    
    print("\nCleanup completed successfully!")

if __name__ == "__main__":
    main()
