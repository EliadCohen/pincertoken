#!/usr/bin/env python3
"""
QR Code Text Extractor

A utility to extract text from QR codes in images.
Supports single image processing or batch processing of multiple images.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np
import yaml
import base64
import urllib.parse
from google.protobuf.message import DecodeError
import google.protobuf.message

# Simple protobuf parser for Google Authenticator migration format
def parse_varint(data, offset):
    """Parse a varint from the data at the given offset."""
    result = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, offset

def parse_length_delimited(data, offset):
    """Parse a length-delimited field from the data."""
    length, offset = parse_varint(data, offset)
    return data[offset:offset + length], offset + length

def decode_google_authenticator_migration(data):
    """Decode Google Authenticator migration protobuf data."""
    accounts = []
    offset = 0
    
    while offset < len(data):
        # Read field header
        if offset >= len(data):
            break
            
        field_header, offset = parse_varint(data, offset)
        field_number = field_header >> 3
        wire_type = field_header & 0x7
        
        if field_number == 1 and wire_type == 2:  # otpParameters (repeated)
            otp_data, offset = parse_length_delimited(data, offset)
            account = decode_otp_parameters(otp_data)
            if account:
                accounts.append(account)
        elif field_number == 2 and wire_type == 0:  # version
            version, offset = parse_varint(data, offset)
        elif field_number == 3 and wire_type == 0:  # batchSize
            batch_size, offset = parse_varint(data, offset)
        elif field_number == 4 and wire_type == 0:  # batchIndex
            batch_index, offset = parse_varint(data, offset)
        elif field_number == 5 and wire_type == 0:  # batchId
            batch_id, offset = parse_varint(data, offset)
        else:
            # Skip unknown fields
            if wire_type == 0:  # varint
                _, offset = parse_varint(data, offset)
            elif wire_type == 2:  # length-delimited
                _, offset = parse_length_delimited(data, offset)
            else:
                break
    
    return accounts

def decode_otp_parameters(data):
    """Decode OTP parameters from protobuf data."""
    account = {}
    offset = 0
    
    while offset < len(data):
        if offset >= len(data):
            break
            
        field_header, offset = parse_varint(data, offset)
        field_number = field_header >> 3
        wire_type = field_header & 0x7
        
        if field_number == 1 and wire_type == 2:  # secret
            secret_data, offset = parse_length_delimited(data, offset)
            account['secret'] = base64.b32encode(secret_data).decode('utf-8')
        elif field_number == 2 and wire_type == 2:  # name
            name_data, offset = parse_length_delimited(data, offset)
            account['name'] = name_data.decode('utf-8', errors='ignore')
        elif field_number == 3 and wire_type == 2:  # issuer
            issuer_data, offset = parse_length_delimited(data, offset)
            account['issuer'] = issuer_data.decode('utf-8', errors='ignore')
        elif field_number == 4 and wire_type == 0:  # algorithm
            algorithm, offset = parse_varint(data, offset)
            algorithm_map = {0: 'SHA1', 1: 'SHA1', 2: 'SHA256', 3: 'SHA512'}
            account['algorithm'] = algorithm_map.get(algorithm, 'SHA1')
        elif field_number == 5 and wire_type == 0:  # digits
            digits, offset = parse_varint(data, offset)
            account['digits'] = digits
        elif field_number == 6 and wire_type == 0:  # type
            otp_type, offset = parse_varint(data, offset)
            type_map = {0: 'HOTP', 1: 'TOTP', 2: 'TOTP'}
            account['type'] = type_map.get(otp_type, 'TOTP')
        elif field_number == 7 and wire_type == 0:  # counter
            counter, offset = parse_varint(data, offset)
            account['counter'] = counter
        else:
            # Skip unknown fields
            if wire_type == 0:  # varint
                _, offset = parse_varint(data, offset)
            elif wire_type == 2:  # length-delimited
                _, offset = parse_length_delimited(data, offset)
            else:
                break
    
    return account

class QRExtractor:
    """Extract text from QR codes in images."""
    
    def __init__(self, verbose=False):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        self.qr_detector = cv2.QRCodeDetector()
        self.verbose = verbose
    
    def extract_qr_from_image(self, image_path: str) -> List[str]:
        """
        Extract all QR code text from a single image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of decoded text strings from QR codes found in the image
        """
        try:
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                print(f"Warning: Could not load image {image_path}")
                return []
            
            if self.verbose:
                print(f"Processing {os.path.basename(image_path)} - Image size: {image.shape}")
            
            # Try multiple detection strategies
            texts = []
            
            # Strategy 1: Direct detection on original image
            texts.extend(self._try_detection(image, "original"))
            
            # Strategy 2: Convert to grayscale and try again
            if not texts:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                texts.extend(self._try_detection(gray, "grayscale"))
            
            # Strategy 3: Apply contrast enhancement
            if not texts:
                enhanced = self._enhance_contrast(image)
                texts.extend(self._try_detection(enhanced, "enhanced"))
            
            # Strategy 4: Try with different scales
            if not texts:
                for scale in [0.5, 1.5, 2.0]:
                    if texts:
                        break
                    width = int(image.shape[1] * scale)
                    height = int(image.shape[0] * scale)
                    resized = cv2.resize(image, (width, height))
                    texts.extend(self._try_detection(resized, f"scale_{scale}"))
            
            # Strategy 5: Try with binary threshold
            if not texts:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                texts.extend(self._try_detection(binary, "binary"))
            
            # Remove duplicates while preserving order
            unique_texts = []
            seen = set()
            for text in texts:
                if text not in seen:
                    unique_texts.append(text)
                    seen.add(text)
            
            return unique_texts
            
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            return []
    
    def _try_detection(self, image, strategy_name):
        """Try QR code detection with the given image and strategy."""
        texts = []
        
        try:
            # Try multi-detection first
            retval, decoded_info, points, straight_qrcode = self.qr_detector.detectAndDecodeMulti(image)
            
            if retval:
                if self.verbose:
                    print(f"  ✓ {strategy_name}: Multi-detection succeeded")
                if isinstance(decoded_info, (list, tuple)):
                    for info in decoded_info:
                        if info:  # Only add non-empty strings
                            texts.append(info)
                elif decoded_info:  # Single QR code
                    texts.append(decoded_info)
            else:
                # Try single detection
                retval, decoded_info, points = self.qr_detector.detectAndDecode(image)
                if retval and decoded_info:
                    if self.verbose:
                        print(f"  ✓ {strategy_name}: Single detection succeeded")
                    texts.append(decoded_info)
                else:
                    if self.verbose:
                        print(f"  ✗ {strategy_name}: No QR codes detected")
        except Exception as e:
            if self.verbose:
                print(f"  ✗ {strategy_name}: Detection failed with error: {e}")
        
        return texts
    
    def _enhance_contrast(self, image):
        """Enhance image contrast to improve QR code detection."""
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        # Split channels
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        
        # Merge channels and convert back to BGR
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        return enhanced
    
    def decode_qr_texts(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Decode QR code texts into structured data."""
        decoded_data = []
        
        for text in texts:
            try:
                if text.startswith('otpauth-migration://'):
                    # Google Authenticator migration format
                    parsed_url = urllib.parse.urlparse(text)
                    if parsed_url.query:
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        if 'data' in query_params:
                            # Decode base64 data
                            encoded_data = query_params['data'][0]
                            # Add padding if needed
                            missing_padding = len(encoded_data) % 4
                            if missing_padding:
                                encoded_data += '=' * (4 - missing_padding)
                            
                            try:
                                decoded_bytes = base64.b64decode(encoded_data)
                                accounts = decode_google_authenticator_migration(decoded_bytes)
                                for account in accounts:
                                    decoded_data.append({
                                        'type': 'google_authenticator_migration',
                                        'format': 'TOTP',
                                        'name': account.get('name', ''),
                                        'issuer': account.get('issuer', ''),
                                        'secret': account.get('secret', ''),
                                        'algorithm': account.get('algorithm', 'SHA1'),
                                        'digits': account.get('digits', 6),
                                        'period': 30,  # TOTP default
                                        'counter': account.get('counter', 0),
                                        'original_text': text
                                    })
                            except Exception as e:
                                decoded_data.append({
                                    'type': 'google_authenticator_migration',
                                    'format': 'UNKNOWN',
                                    'error': f"Failed to decode: {str(e)}",
                                    'original_text': text
                                })
                                
                elif text.startswith('otpauth://'):
                    # Standard otpauth URL format
                    parsed_url = urllib.parse.urlparse(text)
                    path_parts = parsed_url.path.lstrip('/').split('/')
                    issuer = path_parts[0] if path_parts else ''
                    account_name = path_parts[1] if len(path_parts) > 1 else ''
                    
                    query_params = urllib.parse.parse_qs(parsed_url.query)
                    
                    decoded_data.append({
                        'type': 'otpauth',
                        'format': parsed_url.netloc.upper(),  # TOTP or HOTP
                        'name': account_name,
                        'issuer': issuer,
                        'secret': query_params.get('secret', [''])[0],
                        'algorithm': query_params.get('algorithm', ['SHA1'])[0],
                        'digits': int(query_params.get('digits', ['6'])[0]),
                        'period': int(query_params.get('period', ['30'])[0]),
                        'counter': int(query_params.get('counter', ['0'])[0]),
                        'original_text': text
                    })
                else:
                    # Plain text or unknown format
                    decoded_data.append({
                        'type': 'text',
                        'format': 'PLAIN',
                        'content': text,
                        'original_text': text
                    })
                    
            except Exception as e:
                decoded_data.append({
                    'type': 'error',
                    'format': 'UNKNOWN',
                    'error': str(e),
                    'original_text': text
                })
        
        return decoded_data
    
    def save_yaml_output(self, decoded_data: List[Dict[str, Any]], output_file: str):
        """Save decoded QR code data to YAML format."""
        output_data = {
            'qr_codes': decoded_data,
            'metadata': {
                'total_codes': len(decoded_data),
                'extraction_date': __import__('datetime').datetime.now().isoformat()
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(output_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def process_single_image(self, image_path: str, output_file: Optional[str] = None, yaml_output: Optional[str] = None) -> List[str]:
        """
        Process a single image and optionally save results to file.
        
        Args:
            image_path: Path to the image file
            output_file: Optional output file path
            yaml_output: Optional YAML output file path
            
        Returns:
            List of extracted text strings
        """
        texts = self.extract_qr_from_image(image_path)
        
        if texts:
            print(f"Found {len(texts)} QR code(s) in {image_path}:")
            for i, text in enumerate(texts, 1):
                print(f"  QR {i}: {text}")
        else:
            print(f"No QR codes found in {image_path}")
        
        if output_file and texts:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"QR codes from {image_path}:\n")
                for i, text in enumerate(texts, 1):
                    f.write(f"QR {i}: {text}\n")
                f.write("\n")
        
        if yaml_output and texts:
            decoded_data = self.decode_qr_texts(texts)
            self.save_yaml_output(decoded_data, yaml_output)
            print(f"YAML output saved to: {yaml_output}")
        
        return texts
    
    def process_batch(self, input_dir: str, output_file: str, recursive: bool = False, yaml_output: Optional[str] = None) -> dict:
        """
        Process a batch of images from a directory.
        
        Args:
            input_dir: Directory containing images
            output_file: Output text file path
            recursive: Whether to search subdirectories
            
        Returns:
            Dictionary mapping image paths to extracted texts
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"Error: Directory {input_dir} does not exist")
            return {}
        
        # Find all image files
        image_files = []
        if recursive:
            for ext in self.supported_formats:
                image_files.extend(input_path.rglob(f"*{ext}"))
                image_files.extend(input_path.rglob(f"*{ext.upper()}"))
        else:
            for ext in self.supported_formats:
                image_files.extend(input_path.glob(f"*{ext}"))
                image_files.extend(input_path.glob(f"*{ext.upper()}"))
        
        if not image_files:
            print(f"No image files found in {input_dir}")
            return {}
        
        print(f"Processing {len(image_files)} image(s)...")
        
        # Process each image
        results = {}
        total_qr_codes = 0
        all_decoded_data = []
        
        with open(output_file, 'w', encoding='utf-8') as f:
            
            for image_path in sorted(image_files):
                image_path_str = str(image_path)
                texts = self.extract_qr_from_image(image_path_str)
                results[image_path_str] = texts
                
                if texts:
                    total_qr_codes += len(texts)
                    for text in texts:
                        f.write(f"{text}\n")
                    
                    # Decode for YAML output
                    if yaml_output:
                        decoded_data = self.decode_qr_texts(texts)
                        for item in decoded_data:
                            item['source_image'] = image_path_str
                            item['source_filename'] = image_path.name
                        all_decoded_data.extend(decoded_data)
                    
                    print(f"✓ {image_path.name}: {len(texts)} QR code(s)")
                else:
                    print(f"✗ {image_path.name}: No QR codes found")
        
        # Save YAML output if requested
        if yaml_output and all_decoded_data:
            self.save_yaml_output(all_decoded_data, yaml_output)
            print(f"YAML output saved to: {yaml_output}")
        
        print(f"\nProcessing complete!")
        print(f"Total images processed: {len(image_files)}")
        print(f"Total QR codes found: {total_qr_codes}")
        print(f"Results saved to: {output_file}")
        
        return results

def main():
    parser = argparse.ArgumentParser(description="Extract text from QR codes in images")
    parser.add_argument("input", help="Input image file or directory")
    parser.add_argument("-o", "--output", help="Output text file", default="qr_results.txt")
    parser.add_argument("-y", "--yaml", help="Output decoded QR codes to YAML file")
    parser.add_argument("-r", "--recursive", action="store_true", 
                       help="Search subdirectories recursively (batch mode only)")
    parser.add_argument("--batch", action="store_true", 
                       help="Process all images in the input directory")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose output for debugging")
    
    args = parser.parse_args()
    
    extractor = QRExtractor(verbose=args.verbose)
    
    if args.batch or os.path.isdir(args.input):
        # Batch processing
        extractor.process_batch(args.input, args.output, args.recursive, args.yaml)
    else:
        # Single image processing
        if not os.path.isfile(args.input):
            print(f"Error: File {args.input} does not exist")
            sys.exit(1)
        
        extractor.process_single_image(args.input, args.output, args.yaml)

if __name__ == "__main__":
    main() 