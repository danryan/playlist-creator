#!/usr/bin/env python3
"""Wrapper to call generate_apple_music_token with --save flag."""

import sys

from generate_apple_music_token import main

if __name__ == "__main__":
    sys.argv.append("--save")
    main()
