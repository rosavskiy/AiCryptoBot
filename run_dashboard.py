#!/usr/bin/env python3
"""
Run Web Dashboard
=================
Standalone script to run web dashboard for testing
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.web.app import run_web_server

if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    print("="*60)
    print("   AI CRYPTO BOT - WEB DASHBOARD")
    print("="*60)
    print()
    print("Starting web server...")
    print("Dashboard will be available at: http://localhost:5000")
    print()
    print("Press Ctrl+C to stop")
    print("="*60)
    print()
    
    try:
        run_web_server(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)
