"""PenguScript LSP Server Main Entry Point."""

import argparse
import sys
from .server import server


def main():
    """Parses command line arguments and runs the LSP server."""
    parser = argparse.ArgumentParser(description="PenguScript Language Server Protocol (LSP)")
    parser.add_argument("--stdio", action="store_true", default=True, help="Run LSP server over stdio (default)")
    parser.add_argument("--tcp", action="store_true", help="Run LSP server over TCP socket")
    parser.add_argument("--host", default="127.0.0.1", help="TCP bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=2087, help="TCP bind port (default: 2087)")

    args = parser.parse_args()

    if args.tcp:
        print(f"Starting PenguScript LSP server on {args.host}:{args.port}...", file=sys.stderr)
        server.start_tcp(args.host, args.port)
    else:
        server.start_io()


if __name__ == "__main__":
    main()
