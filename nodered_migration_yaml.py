#!/usr/bin/env python3
"""
Node-RED Migration Script with YAML Configuration Support
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

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

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
            'replacements_made': 0,
            'rules_applied': {}
        }
    
    def add_migration_rule(self, old_pattern: str, new_pattern: str, description: str = ""):
        """Add a search/replace rule for migration"""
        rule_id = len(self.migration_rules)
        self.migration_rules.append({
            'id': rule_id,
            'old': old_pattern,
            'new': new_pattern,
            'description': description,
            'regex': re.compile(old_pattern, re.MULTILINE | re.DOTALL)
        })
        self.stats['rules_applied'][rule_id] = 0
        logger.info(f"Added migration rule {rule_id}: {description}")
    
    def load_rules_from_yaml(self, yaml_file: str):
        """Load migration rules from YAML configuration"""
        if not YAML_AVAILABLE:
            logger.error("PyYAML not installed. Install with: pip install PyYAML")
            return False
        
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'migration_rules' in config:
                for rule in config['migration_rules']:
                    self.add_migration_rule(
                        rule['old_pattern'],
                        rule['new_pattern'],
                        rule.get('description', '')
                    )
                logger.info(f"Loaded {len(config['migration_rules'])} rules from {yaml_file}")
                return True
        except Exception as e:
            logger.error(f"Failed to load YAML rules from {yaml_file}: {e}")
            return False
    
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
        applied_rules = []
        
        # Apply all migration rules
        for rule in self.migration_rules:
            matches = rule['regex'].findall(func_code)
            if matches:
                func_code = rule['regex'].sub(rule['new'], func_code)
                self.stats['replacements_made'] += len(matches)
                self.stats['rules_applied'][rule['id']] += len(matches)
                applied_rules.append(rule['description'])
                logger.debug(f"Applied rule '{rule['description']}' to node {node.get('name', node.get('id'))}")
                updated = True
        
        if updated:
            node['func'] = func_code
            self.stats['nodes_updated'] += 1
            logger.info(f"Updated function node '{node.get('name', node.get('id'))}' - Applied rules: {', '.join(applied_rules)}")
            
            # Add a comment to track migration
            migration_comment = f"\n// Migrated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            if migration_comment not in node['func']:
                node['func'] += migration_comment
        
        return updated
    
    def migrate_flow_data(self, flow_data: Any) -> bool:
        """Migrate flow data (can be a list of flows or a single flow)"""
        updated = False
        
        if isinstance(flow_data, list):
            # Multiple flows or nodes
            for item in flow_data:
                if isinstance(item, dict):
                    if item.get('type') == 'function':
                        if self.migrate_function_node(item):
                            updated = True
                    elif 'nodes' in item:
                        # This is a flow with nodes
                        if self.migrate_single_flow(item):
                            updated = True
        elif isinstance(flow_data, dict):
            # Single flow or node
            if flow_data.get('type') == 'function':
                if self.migrate_function_node(flow_data):
                    updated = True
            else:
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
        
        # Filter out backup files
        flow_files = [f for f in flow_files if '.backup_' not in f]
        
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
        print("\n" + "="*60)
        print("MIGRATION STATISTICS")
        print("="*60)
        print(f"Flows processed: {self.stats['flows_processed']}")
        print(f"Function nodes found: {self.stats['function_nodes_found']}")
        print(f"Nodes updated: {self.stats['nodes_updated']}")
        print(f"Total replacements made: {self.stats['replacements_made']}")
        print("\nRules Applied:")
        print("-" * 40)
        for rule in self.migration_rules:
            count = self.stats['rules_applied'][rule['id']]
            status = "✓" if count > 0 else "○"
            print(f"{status} Rule {rule['id']}: {rule['description']} ({count} times)")
        print("="*60)

def setup_default_migration_rules(migrator: NodeRedMigrator):
    """Setup common API migration rules for RedRat system"""
    
    # RedRat specific migrations
    migrator.add_migration_rule(
        r'http://localhost:5000/api/v1/',
        'http://localhost:5000/api/',
        'Update API base URL from v1 to current'
    )
    
    # Update command structure for new RedRat API
    migrator.add_migration_rule(
        r'msg\.payload\s*=\s*\{\s*["\']command["\']\s*:\s*["\']([^"\']+)["\']\s*,\s*["\']remote["\']\s*:\s*["\']([^"\']+)["\']\s*\}',
        r'''msg.payload = {
    "remote_id": "\2",
    "command": "\1",
    "redrat_device_id": 1,
    "ir_port": 1,
    "power": 100
}''',
        'Update command payload structure for new RedRat API'
    )
    
    # Update endpoint paths
    migrator.add_migration_rule(
        r'/send_command',
        '/api/commands',
        'Update command endpoint path'
    )
    
    migrator.add_migration_rule(
        r'/get_status',
        '/api/redrat/devices',
        'Update device status endpoint'
    )
    
    migrator.add_migration_rule(
        r'/get_remotes',
        '/api/remotes',
        'Update remotes endpoint'
    )
    
    # Update authentication method (remove old Bearer tokens)
    migrator.add_migration_rule(
        r'msg\.headers\s*=\s*\{\s*["\']Authorization["\']\s*:\s*["\']Bearer\s+[^"\']+["\']\s*\}',
        '''msg.headers = {
    "Content-Type": "application/json"
    // Authentication now handled by session cookies
}''',
        'Update authentication method from Bearer tokens to session cookies'
    )
    
    # Update old error handling
    migrator.add_migration_rule(
        r'if\s*\(\s*msg\.statusCode\s*!==\s*200\s*\)',
        'if (msg.statusCode !== 200)',
        'Standardize status code checking'
    )

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Migrate Node-RED flows to new API',
        epilog='''
Examples:
  python nodered_migration_yaml.py flows.json
  python nodered_migration_yaml.py ./flows/ --pattern "*.json"
  python nodered_migration_yaml.py flows.json --rules migration_rules.yaml
  python nodered_migration_yaml.py ./flows/ --no-backup --verbose
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('input', help='Input file or directory path')
    parser.add_argument('--rules', help='YAML file with migration rules')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup files')
    parser.add_argument('--pattern', default='*.json', help='File pattern for directory migration')
    parser.add_argument('--custom-rules-only', action='store_true', help='Only apply custom rules from YAML')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize migrator
    migrator = NodeRedMigrator()
    
    # Load rules from YAML if specified
    if args.rules:
        if not migrator.load_rules_from_yaml(args.rules):
            sys.exit(1)
    elif not args.custom_rules_only:
        # Use default rules if no YAML file specified
        setup_default_migration_rules(migrator)
    
    if not migrator.migration_rules:
        logger.error("No migration rules defined!")
        print("Use --rules to specify a YAML configuration file, or remove --custom-rules-only to use defaults")
        sys.exit(1)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be modified")
        # TODO: Implement dry run functionality
    
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
