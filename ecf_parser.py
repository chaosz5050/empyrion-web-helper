#!/usr/bin/env python3
"""
ECF Parser for Empyrion ItemsConfig.ecf files
Handles the complex ECF format used by Empyrion Galactic Survival
"""

import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ECFParser:
    """
    Parser for Empyrion ECF (Empyrion Configuration File) format.
    
    Handles ItemsConfig.ecf files with template inheritance and complex property values.
    """
    
    def __init__(self):
        # Properties we care about for safe editing
        self.safe_properties = {
            'StackSize': 'stacksize',
            'Mass': 'mass', 
            'Volume': 'volume',
            'MarketPrice': 'marketprice'
        }
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse an ItemsConfig.ecf file and return structured data.
        
        Args:
            file_path (str): Path to the ItemsConfig.ecf file
            
        Returns:
            Dict containing parsed items, templates, and metadata
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Parsing ECF file: {file_path} ({len(content)} characters)")
            
            # Parse all item blocks
            logger.info("Extracting item blocks from ECF content...")
            raw_items = self._extract_item_blocks(content)
            logger.info(f"Found {len(raw_items)} item blocks")
            
            if len(raw_items) > 10000:
                logger.warning(f"Large number of item blocks detected: {len(raw_items)}. This may take a while to process.")
            
            # Process items and templates
            items = []
            templates = {}
            
            logger.info("Processing item blocks...")
            for i, raw_item in enumerate(raw_items):
                # Log progress for large files
                if i > 0 and i % 1000 == 0:
                    logger.info(f"Processed {i}/{len(raw_items)} item blocks ({i/len(raw_items)*100:.1f}%)")
                processed_item = self._process_item_block(raw_item)
                if processed_item:
                    if processed_item.get('is_template'):
                        templates[processed_item['name']] = processed_item
                    
                    items.append(processed_item)
            
            logger.info(f"Finished processing {len(raw_items)} item blocks. Found {len(templates)} templates.")
            
            # Resolve template inheritance
            logger.info("Resolving template inheritance...")
            resolved_items = self._resolve_template_inheritance(items, templates)
            logger.info(f"Template inheritance resolved. Final item count: {len(resolved_items)}")
            
            logger.info(f"Successfully parsed {len(resolved_items)} items ({len(templates)} templates)")
            
            return {
                'items': resolved_items,
                'templates': templates,
                'total_count': len(resolved_items),
                'template_count': len(templates),
                'item_count': len(resolved_items) - len(templates)
            }
            
        except Exception as e:
            logger.error(f"Error parsing ECF file: {e}", exc_info=True)
            raise
    
    def _extract_item_blocks(self, content: str) -> List[str]:
        """
        Extract individual item blocks from ECF content.
        
        Each block starts with '{ Item Id:' or '{ +Item Id:' and ends with '}'
        """
        blocks = []
        lines = content.split('\n')
        current_block = []
        in_block = False
        brace_count = 0
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Skip comments and empty lines when not in block
            if not in_block and (not line_stripped or line_stripped.startswith('#')):
                continue
            
            # Check for block start
            if re.match(r'^\{\s*\+?Item\s+Id:', line_stripped, re.IGNORECASE):
                if in_block:
                    logger.warning(f"Found nested item block at line {line_num}")
                
                in_block = True
                current_block = [line]
                brace_count = 1
                continue
            
            if in_block:
                current_block.append(line)
                
                # Count braces to handle nested structures
                brace_count += line.count('{') - line.count('}')
                
                # Block complete when braces balance
                if brace_count == 0:
                    blocks.append('\n'.join(current_block))
                    current_block = []
                    in_block = False
        
        # Handle unclosed block
        if in_block:
            logger.warning("Found unclosed item block at end of file")
            if current_block:
                blocks.append('\n'.join(current_block))
        
        return blocks
    
    def _process_item_block(self, block: str) -> Optional[Dict[str, Any]]:
        """
        Process a single item block and extract relevant properties.
        """
        try:
            lines = block.split('\n')
            if not lines:
                return None
            
            # Parse the header line
            header = lines[0].strip()
            header_match = re.match(r'^\{\s*(\+?)Item\s+Id:\s*(\d+),\s*Name:\s*(\w+)(?:,\s*Ref:\s*(\w+))?', header, re.IGNORECASE)
            
            if not header_match:
                logger.warning(f"Could not parse item header: {header}")
                return None
            
            is_template_marker, item_id, name, template_ref = header_match.groups()
            
            # Determine if this is a template
            # A template has '+' marker, no Ref, and name ends with 'Template'
            is_template = (is_template_marker == '+' and 
                          not template_ref and 
                          name.endswith('Template'))
            
            item = {
                'id': item_id,
                'name': name,
                'type': 'template' if is_template else 'item',
                'is_template': is_template,
                'template': template_ref or '',
                'raw_properties': {}
            }
            
            # Initialize safe properties
            for safe_prop in self.safe_properties.values():
                item[safe_prop] = ''
            
            # Parse properties from remaining lines
            for line in lines[1:]:
                line_stripped = line.strip()
                
                # Skip comments, empty lines, and closing brace
                if (not line_stripped or 
                    line_stripped.startswith('#') or 
                    line_stripped == '}'):
                    continue
                
                # Parse property line
                prop_name, prop_value = self._parse_property_line(line_stripped)
                if prop_name and prop_name in self.safe_properties:
                    safe_key = self.safe_properties[prop_name]
                    item[safe_key] = str(prop_value) if prop_value is not None else ''
                    item['raw_properties'][prop_name] = prop_value
            
            return item
            
        except Exception as e:
            logger.error(f"Error processing item block: {e}")
            logger.debug(f"Block content: {block[:200]}...")
            return None
    
    def _parse_property_line(self, line: str) -> tuple:
        """
        Parse a property line and extract the main value.
        
        Examples:
        'StackSize: 40000' -> ('StackSize', '40000')
        'Mass: 6.51, type: float, display: true, formatter: Kilogram' -> ('Mass', '6.51')
        'MarketPrice: 100, display: true' -> ('MarketPrice', '100')
        """
        try:
            # Split on first colon
            if ':' not in line:
                return None, None
            
            prop_name, prop_value_part = line.split(':', 1)
            prop_name = prop_name.strip()
            prop_value_part = prop_value_part.strip()
            
            if not prop_value_part:
                return prop_name, ''
            
            # Handle complex property values with metadata
            # Split on comma and take the first part as the main value
            main_value = prop_value_part.split(',')[0].strip()
            
            # Clean up the value (remove quotes, etc.)
            main_value = main_value.strip('\'"')
            
            return prop_name, main_value
            
        except Exception as e:
            logger.debug(f"Could not parse property line: {line} - {e}")
            return None, None
    
    def _resolve_template_inheritance(self, items: List[Dict], templates: Dict[str, Dict]) -> List[Dict]:
        """
        Resolve template inheritance for all items.
        
        Items with a 'template' reference inherit properties from that template,
        but their own properties override the template values.
        """
        resolved_items = []
        
        for item in items:
            resolved_item = item.copy()
            
            # If item references a template, inherit properties
            if item['template'] and item['template'] in templates:
                template = templates[item['template']]
                
                # Inherit template properties, but don't override existing item properties
                for prop in self.safe_properties.values():
                    if not resolved_item.get(prop) and template.get(prop):
                        resolved_item[prop] = template[prop]
            
            resolved_items.append(resolved_item)
        
        return resolved_items
    
    def write_file(self, file_path: str, items: List[Dict], original_content: str = None) -> bool:
        """
        Write items back to ECF format.
        
        This is a placeholder for future implementation.
        For safety, we'll implement this carefully later.
        """
        # TODO: Implement ECF writing with proper formatting
        logger.warning("ECF writing not yet implemented")
        return False


# Test function
def test_parser():
    """Test the ECF parser with a sample file."""
    import os
    
    test_file = os.path.join(os.getcwd(), 'temp', 'ItemsConfig.ecf')
    if os.path.exists(test_file):
        parser = ECFParser()
        try:
            result = parser.parse_file(test_file)
            print(f"Successfully parsed {result['total_count']} items")
            print(f"Templates: {result['template_count']}, Items: {result['item_count']}")
            
            # Show first few items
            for item in result['items'][:5]:
                print(f"ID {item['id']}: {item['name']} ({item['type']}) - Stack: {item['stacksize']}, Mass: {item['mass']}")
                
        except Exception as e:
            print(f"Parser test failed: {e}")
    else:
        print(f"Test file not found: {test_file}")


if __name__ == '__main__':
    test_parser()