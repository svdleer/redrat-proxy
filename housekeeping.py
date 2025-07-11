#!/usr/bin/env python3
"""
RedRat Proxy Housekeeping Script

This script performs cleanup tasks:
1. Removes unused temporary files
2. Cleans up unused database sessions
3. Reports file usage statistics
"""

import os
import sys
import datetime
import mysql.connector
import argparse

def connect_to_db():
    """Connect to the MySQL database"""
    try:
        conn = mysql.connector.connect(
            host=os.environ.get('MYSQL_HOST', 'host.docker.internal'),
            user=os.environ.get('MYSQL_USER', 'redrat'),
            password=os.environ.get('MYSQL_PASSWORD', 'redratpass'),
            database=os.environ.get('MYSQL_DB', 'redrat_proxy')
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def cleanup_sessions(conn, days_old=7):
    """Clean up expired sessions from the database"""
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        
        # Get count of expired sessions before deletion
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE expires_at < %s", (cutoff_date,))
        count_before = cursor.fetchone()[0]
        
        # Delete expired sessions
        cursor.execute("DELETE FROM sessions WHERE expires_at < %s", (cutoff_date,))
        conn.commit()
        
        print(f"✅ Removed {count_before} expired sessions older than {days_old} days")
        return True
    except mysql.connector.Error as err:
        print(f"Error cleaning up sessions: {err}")
        return False

def cleanup_temp_files(base_dir, days_old=7):
    """Clean up temporary files older than the specified days"""
    temp_dirs = [
        os.path.join(base_dir, 'app', 'static', 'uploads', 'temp'),
        os.path.join(base_dir, 'app', 'static', 'remote_images', 'temp')
    ]
    
    now = datetime.datetime.now()
    cutoff_date = now - datetime.timedelta(days=days_old)
    total_removed = 0
    
    for temp_dir in temp_dirs:
        if not os.path.exists(temp_dir):
            print(f"Creating temporary directory: {temp_dir}")
            os.makedirs(temp_dir, exist_ok=True)
            continue
            
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                file_modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_modified < cutoff_date:
                    os.remove(file_path)
                    total_removed += 1
    
    print(f"✅ Removed {total_removed} temporary files older than {days_old} days")

def cleanup_unused_irdb_files(conn, base_dir):
    """Clean up IRDB files that are no longer referenced in the database"""
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Get all IRDB files from the database
        cursor.execute("SELECT filepath FROM irdb_files")
        db_files = set(row[0] for row in cursor.fetchall())
        
        # Physical IRDB files location
        irdb_dir = os.path.join(base_dir, 'app', 'static', 'uploads', 'irdb')
        if not os.path.exists(irdb_dir):
            print(f"IRDB directory not found: {irdb_dir}")
            return False
            
        # Check physical files
        removed_count = 0
        for filename in os.listdir(irdb_dir):
            if filename.endswith('.irdb'):
                file_path = os.path.join('uploads', 'irdb', filename)  # Database stores relative paths
                abs_path = os.path.join(irdb_dir, filename)
                
                # If file exists on disk but not in DB, it's orphaned
                if file_path not in db_files and os.path.isfile(abs_path):
                    # Create a backup directory
                    backup_dir = os.path.join(base_dir, 'app', 'static', 'uploads', 'backup_irdb')
                    os.makedirs(backup_dir, exist_ok=True)
                    
                    # Move to backup instead of deleting
                    backup_path = os.path.join(backup_dir, filename)
                    os.rename(abs_path, backup_path)
                    removed_count += 1
        
        print(f"✅ Moved {removed_count} orphaned IRDB files to backup directory")
        return True
    except mysql.connector.Error as err:
        print(f"Error cleaning up IRDB files: {err}")
        return False

def cleanup_unused_remote_images(conn, base_dir):
    """Clean up remote images that are no longer referenced in the database"""
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Get all remote images from the database
        cursor.execute("SELECT image_path FROM remotes WHERE image_path IS NOT NULL")
        db_images = set(row[0] for row in cursor.fetchall())
        
        # Physical remote images location
        images_dir = os.path.join(base_dir, 'app', 'static', 'remote_images')
        if not os.path.exists(images_dir):
            print(f"Remote images directory not found: {images_dir}")
            return False
            
        # Check physical files
        removed_count = 0
        for filename in os.listdir(images_dir):
            if filename.endswith(('.png', '.jpg', '.jpeg', '.gif')) and filename != 'logo.png':
                file_path = os.path.join('remote_images', filename)  # Database stores paths like this
                abs_path = os.path.join(images_dir, filename)
                
                # If file exists on disk but not in DB, it's orphaned
                if file_path not in db_images and os.path.isfile(abs_path):
                    # Create a backup directory
                    backup_dir = os.path.join(base_dir, 'app', 'static', 'remote_images', 'backup')
                    os.makedirs(backup_dir, exist_ok=True)
                    
                    # Move to backup instead of deleting
                    backup_path = os.path.join(backup_dir, filename)
                    os.rename(abs_path, backup_path)
                    removed_count += 1
        
        print(f"✅ Moved {removed_count} orphaned remote images to backup directory")
        return True
    except mysql.connector.Error as err:
        print(f"Error cleaning up remote images: {err}")
        return False

def get_storage_stats(base_dir):
    """Get storage statistics for the application"""
    stats = {
        'uploads': {'count': 0, 'size': 0},
        'remote_images': {'count': 0, 'size': 0},
        'irdb_files': {'count': 0, 'size': 0}
    }
    
    # Uploads directory stats
    uploads_dir = os.path.join(base_dir, 'app', 'static', 'uploads')
    if os.path.exists(uploads_dir):
        for root, _, files in os.walk(uploads_dir):
            for file in files:
                stats['uploads']['count'] += 1
                stats['uploads']['size'] += os.path.getsize(os.path.join(root, file))
                if file.endswith('.irdb'):
                    stats['irdb_files']['count'] += 1
                    stats['irdb_files']['size'] += os.path.getsize(os.path.join(root, file))
    
    # Remote images directory stats
    images_dir = os.path.join(base_dir, 'app', 'static', 'remote_images')
    if os.path.exists(images_dir):
        for root, _, files in os.walk(images_dir):
            for file in files:
                if file.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    stats['remote_images']['count'] += 1
                    stats['remote_images']['size'] += os.path.getsize(os.path.join(root, file))
    
    return stats

def print_storage_stats(stats):
    """Print storage statistics in a readable format"""
    print("\n=== Storage Statistics ===")
    print(f"Total uploads: {stats['uploads']['count']} files ({format_size(stats['uploads']['size'])})")
    print(f"Remote images: {stats['remote_images']['count']} files ({format_size(stats['remote_images']['size'])})")
    print(f"IRDB files: {stats['irdb_files']['count']} files ({format_size(stats['irdb_files']['size'])})")

def format_size(size_bytes):
    """Format bytes into a human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def main():
    parser = argparse.ArgumentParser(description="RedRat Proxy Housekeeping Script")
    parser.add_argument('--days', type=int, default=7, help='Number of days to consider files as old (default: 7)')
    parser.add_argument('--dry-run', action='store_true', help='Only report what would be done without making changes')
    parser.add_argument('--base-dir', type=str, default=os.getcwd(), help='Base directory of the RedRat Proxy installation')
    args = parser.parse_args()
    
    print("=== RedRat Proxy Housekeeping ===")
    print(f"Base directory: {args.base_dir}")
    print(f"Cleanup threshold: {args.days} days")
    print(f"Dry run: {'Yes' if args.dry_run else 'No'}")
    print("================================")
    
    # Get storage statistics before cleanup
    print("\nGathering statistics before cleanup...")
    stats_before = get_storage_stats(args.base_dir)
    print_storage_stats(stats_before)
    
    if not args.dry_run:
        # Connect to database
        conn = connect_to_db()
        if conn:
            print("\nPerforming cleanup operations...")
            cleanup_sessions(conn, args.days)
            cleanup_unused_irdb_files(conn, args.base_dir)
            cleanup_unused_remote_images(conn, args.base_dir)
            conn.close()
        
        # Cleanup temp files
        cleanup_temp_files(args.base_dir, args.days)
        
        # Get statistics after cleanup
        print("\nGathering statistics after cleanup...")
        stats_after = get_storage_stats(args.base_dir)
        print_storage_stats(stats_after)
        
        # Calculate and show differences
        saved_bytes = stats_before['uploads']['size'] + stats_before['remote_images']['size'] - \
                     (stats_after['uploads']['size'] + stats_after['remote_images']['size'])
        saved_files = stats_before['uploads']['count'] + stats_before['remote_images']['count'] - \
                     (stats_after['uploads']['count'] + stats_after['remote_images']['count'])
        
        print(f"\n✨ Cleanup completed! Saved {format_size(saved_bytes)} across {saved_files} files")
    else:
        print("\nDry run completed. No changes were made.")

if __name__ == "__main__":
    main()
