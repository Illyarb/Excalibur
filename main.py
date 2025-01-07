#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import List, Optional

def create_file(filename: str) -> None:
    Path(f"{filename}.txt").touch()

def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("filename")
    return parser.parse_args(args)

def main(args: Optional[List[str]] = None) -> int:
    parsed_args = parse_args(args)
    if parsed_args.command == "add":
        create_file(parsed_args.filename)
    return 0

if __name__ == "__main__":
    sys.exit(main())

