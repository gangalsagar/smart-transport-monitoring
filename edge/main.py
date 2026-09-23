#!/usr/bin/env python3
"""
Edge AI Node Main Entry Point
==============================
Initializes the Edge AI Device runtime:
1. Loads Edge configuration
2. Initializes Shared Camera / Video source
3. Initializes Shared GPS Service
4. Initializes AI Modules (Defect, Traffic, Incident & ANPR)
5. Starts Offline SQLite Queue & Sync Worker
6. Executes concurrent frame processing loop
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from edge.runtime.orchestrator import EdgeOrchestrator, main

if __name__ == "__main__":
    main()
