# QR Code Text Extractor

A Python utility to extract text from QR codes in images with support for batch processing.

## Features

- Extract text from QR codes in single images or batch process multiple images
- Support for common image formats: JPG, PNG, BMP, TIFF, WebP
- Recursive directory scanning
- Output results to a text file
- Handle multiple QR codes in a single image
- **Robust detection** with multiple strategies:
  - Multiple scaling attempts (0.5x, 1.5x, 2.0x)
  - Grayscale conversion
  - Contrast enhancement
  - Binary thresholding
- Verbose debugging mode to troubleshoot detection issues
- **YAML decoding** for structured output:
  - Automatic detection of Google Authenticator export URLs
  - Decoding of TOTP/HOTP secrets
  - Support for standard `otpauth://` URLs
  - Metadata tracking (source image, extraction date)

## Installation

Make sure you have the required dependencies installed:

```bash
source .venv/bin/activate
pip install opencv-python "numpy<2.0" pyyaml protobuf
```

No additional system libraries are required! The utility uses OpenCV's built-in QR code detector.

## Usage

### Single Image Processing

Process a single image:
```bash
source .venv/bin/activate
python qr_extractor.py image.jpg -o results.txt
```

### Batch Processing

Process all images in a directory:
```bash
source .venv/bin/activate
python qr_extractor.py /path/to/images/ -o results.txt
```

Process all images in a directory and subdirectories:
```bash
source .venv/bin/activate
python qr_extractor.py /path/to/images/ -o results.txt --recursive
```

### Command Line Options

- `input`: Input image file or directory (required)
- `-o, --output`: Output text file (default: qr_results.txt)
- `-y, --yaml`: Output decoded QR codes to YAML file
- `-r, --recursive`: Search subdirectories recursively (batch mode only)
- `--batch`: Force batch processing mode
- `-v, --verbose`: Enable verbose output for debugging detection issues

## Output Formats

### Text Output (default)
Creates a text file with one line per QR code found:
```
QR code text 1
QR code text 2
QR code text 3
...
```

### YAML Output (with -y flag)
Creates a structured YAML file with decoded QR code data:
```yaml
qr_codes:
- type: google_authenticator_migration
  format: TOTP
  name: MyAccount
  issuer: MyService
  secret: JBSWY3DPEHPK3PXP
  algorithm: SHA1
  digits: 6
  period: 30
  counter: 0
  source_image: /path/to/image.jpg
  source_filename: image.jpg
  original_text: otpauth-migration://offline?data=...
metadata:
  total_codes: 1
  extraction_date: '2025-07-14T09:29:57.735678'
```

#### Supported QR Code Types:
- **Google Authenticator Migration**: `otpauth-migration://` URLs with batch export data
- **Standard TOTP/HOTP**: `otpauth://totp/` or `otpauth://hotp/` URLs
- **Plain Text**: Any other QR code content

## Examples

Extract QR codes from a single image:
```bash
source .venv/bin/activate
python qr_extractor.py screenshot.png -o extracted_codes.txt
```

Process all images in the current directory:
```bash
source .venv/bin/activate
python qr_extractor.py . -o all_qr_codes.txt
```

Process images recursively in a photos directory:
```bash
source .venv/bin/activate
python qr_extractor.py ~/Photos/QR_Screenshots/ -o qr_results.txt --recursive
```

Debug detection issues with verbose output:
```bash
source .venv/bin/activate
python qr_extractor.py problem_image.jpg -o debug_results.txt --verbose
```

Extract and decode Google Authenticator QR codes to YAML:
```bash
source .venv/bin/activate
python qr_extractor.py auth_backup.jpg -y decoded_secrets.yaml
```

Process multiple images with both text and YAML output:
```bash
source .venv/bin/activate
python qr_extractor.py ./qr_images/ -o raw_text.txt -y structured_data.yaml
```

## Error Handling

- Images that can't be loaded will show a warning and be skipped
- QR codes that can't be decoded will show a warning and be skipped
- The utility will continue processing other images even if some fail 