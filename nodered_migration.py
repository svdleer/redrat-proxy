#!/usr/bin/env python3
"""
Node-RED Migration Script
Migrates function nodes in Node-RED flows to use new API endpoints and patterns.
"""

import json
import re
import os
import sys
import argparse
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeRedMigrator:
    """Main migration class for Node-RED flows"""
    
    def __init__(self):
        self.migration_rules = []
        self.stats = {
            'flows_processed': 0,
            'nodes_updated': 0,
            'function_nodes_found': 0,
            'replacements_made': 0
        }
    
    def add_migration_rule(self, old_pattern: str, new_pattern: str, description: str = ""):
        """Add a search/replace rule for migration"""
        self.migration_rules.append({
            'old': old_pattern,
            'new': new_pattern,
            'description': description,
            'regex': re.compile(old_pattern, re.MULTILINE | re.DOTALL)
        })
        logger.info(f"Added migration rule: {description}")
    
    def load_flow_file(self, file_path: str) -> Dict[str, Any]:
        """Load a Node-RED flow file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                flow_data = json.load(f)
            logger.info(f"Loaded flow file: {file_path}")
            return flow_data
        except Exception as e:
            logger.error(f"Failed to load flow file {file_path}: {e}")
            raise
    
    def save_flow_file(self, flow_data: Dict[str, Any], file_path: str):
        """Save a Node-RED flow file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(flow_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved flow file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save flow file {file_path}: {e}")
            raise
    
    def create_backup(self, file_path: str) -> str:
        """Create a backup of the original file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    
    def migrate_function_node(self, node: Dict[str, Any]) -> bool:
        """Migrate a single function node"""
        if node.get('type') != 'function':
            return False
        
        self.stats['function_nodes_found'] += 1
        func_code = node.get('func', '')
        original_code = func_code
        updated = False
        
        # Apply all migration rules
        for rule in self.migration_rules:
            matches = rule['regex'].findall(func_code)
            if matches:
                func_code = rule['regex'].sub(rule['new'], func_code)
                self.stats['replacements_made'] += len(matches)
                logger.debug(f"Applied rule '{rule['description']}' to node {node.get('name', node.get('id'))}")
                updated = True
        
        if updated:
            node['func'] = func_code
            self.stats['nodes_updated'] += 1
            logger.info(f"Updated function node: {node.get('name', node.get('id'))}")
            
            # Add a comment to track migration
            migration_comment = f"\n// Migrated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            if migration_comment not in node['func']:
                node['func'] += migration_comment
        
        return updated
    
    def migrate_flow_data(self, flow_data: Any) -> bool:
        """Migrate flow data (can be a list of flows or a single flow)"""
        updated = False
        
        if isinstance(flow_data, list):
            # Multiple flows
            for flow in flow_data:
                if self.migrate_single_flow(flow):
                    updated = True
        elif isinstance(flow_data, dict):
            # Single flow
            if self.migrate_single_flow(flow_data):
                updated = True
        
        return updated
    
    def migrate_single_flow(self, flow: Dict[str, Any]) -> bool:
        """Migrate a single flow object"""
        updated = False
        
        # Handle different flow structures
        nodes = []
        if 'nodes' in flow:
            nodes = flow['nodes']
        elif isinstance(flow, dict) and flow.get('type'):
            nodes = [flow]
        elif isinstance(flow, list):
            nodes = flow
        
        for node in nodes:
            if isinstance(node, dict):
                if self.migrate_function_node(node):
                    updated = True
        
        return updated
    
    def migrate_file(self, file_path: str, create_backup: bool = True) -> bool:
        """Migrate a single Node-RED flow file"""
        logger.info(f"Starting migration of: {file_path}")
        
        # Create backup if requested
        if create_backup:
            self.create_backup(file_path)
        
        # Load flow data
        flow_data = self.load_flow_file(file_path)
        
        # Migrate the flow
        updated = self.migrate_flow_data(flow_data)
        
        if updated:
            # Save the updated flow
            self.save_flow_file(flow_data, file_path)
            logger.info(f"Migration completed for: {file_path}")
        else:
            logger.info(f"No changes needed for: {file_path}")
        
        self.stats['flows_processed'] += 1
        return updated
    
    def migrate_directory(self, directory_path: str, pattern: str = "*.json", create_backup: bool = True):
        """Migrate all Node-RED flow files in a directory"""
        import glob
        
        search_pattern = os.path.join(directory_path, pattern)
        flow_files = glob.glob(search_pattern)
        
        if not flow_files:
            logger.warning(f"No flow files found matching pattern: {search_pattern}")
            return
        
        logger.info(f"Found {len(flow_files)} flow files to migrate")
        
        for file_path in flow_files:
            try:
                self.migrate_file(file_path, create_backup)
            except Exception as e:
                logger.error(f"Failed to migrate {file_path}: {e}")
                continue
    
    def print_stats(self):
        """Print migration statistics"""
        print("\n" + "="*50)
        print("MIGRATION STATISTICS")
        print("="*50)
        print(f"Flows processed: {self.stats['flows_processed']}")
        print(f"Function nodes found: {self.stats['function_nodes_found']}")
        print(f"Nodes updated: {self.stats['nodes_updated']}")
        print(f"Total replacements made: {self.stats['replacements_made']}")
        print("="*50)

def setup_default_migration_rules(migrator: NodeRedMigrator):
    """Setup common API migration rules"""
    
    # Example: Old RedRat API to new API
    migrator.add_migration_rule(
        r'http://localhost:5000/api/v1/',
        'http://localhost:5000/api/',
        'Update API base URL from v1 to current'
    )
    
    # Example: Old command structure
    migrator.add_migration_rule(
        r'msg\.payload = \{\s*"command":\s*"([^"]+)",\s*"remote":\s*"([^"]+)"\s*\}',
        r'msg.payload = {\n    "remote_id": "\2",\n    "command": "\1",\n    "redrat_device_id": 1,\n    "ir_port": 1,\n    "power": 50\n}',
        'Update command payload structure'
    )
    
    # Example: Change HTTP method calls
    migrator.add_migration_rule(
        r'node\.send\(msg\);',
        'node.send(msg);\n// Updated for new API structure',
        'Add migration comment'
    )
    
    # Example: Update authentication headers
    migrator.add_migration_rule(
        r'msg\.headers = \{\s*"Authorization":\s*"Bearer\s+([^"]+)"\s*\}',
        r'msg.headers = {\n    "Content-Type": "application/json"\n    // Note: Authentication now handled by session cookies\n}',
        'Update authentication method'
    )
    
    # Example: Update endpoint paths
    migrator.add_migration_rule(
        r'/send_command',
        '/api/commands',
        'Update command endpoint'
    )
    
    migrator.add_migration_rule(
        r'/get_status',
        '/api/redrat/devices',
        'Update status endpoint'
    )

def setup_custom_migration_rules(migrator: NodeRedMigrator):
    """Setup custom migration rules - modify this function for your specific needs"""
    
    # Add your custom migration rules here
    # Example:
    
    # migrator.add_migration_rule(
    #     r'old_function_name\(',
    #     'new_function_name(',
    #     'Update function name'
    # )
    
    # migrator.add_migration_rule(
    #     r'old_endpoint_url',
    #     'new_endpoint_url',
    #     'Update API endpoint'
    # )
    
    pass

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Migrate Node-RED flows to new API')
    parser.add_argument('input', help='Input file or directory path')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup files')
    parser.add_argument('--pattern', default='*.json', help='File pattern for directory migration')
    parser.add_argument('--custom-rules-only', action='store_true', help='Only apply custom rules')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize migrator
    migrator = NodeRedMigrator()
    
    # Setup migration rules
    if not args.custom_rules_only:
        setup_default_migration_rules(migrator)
    
    setup_custom_migration_rules(migrator)
    
    if not migrator.migration_rules:
        logger.error("No migration rules defined!")
        sys.exit(1)
    
    # Check if input is file or directory
    if os.path.isfile(args.input):
        logger.info(f"Migrating single file: {args.input}")
        migrator.migrate_file(args.input, not args.no_backup)
    elif os.path.isdir(args.input):
        logger.info(f"Migrating directory: {args.input}")
        migrator.migrate_directory(args.input, args.pattern, not args.no_backup)
    else:
        logger.error(f"Input path does not exist: {args.input}")
        sys.exit(1)
    
    # Print statistics
    migrator.print_stats()

if __name__ == '__main__':
    main()
