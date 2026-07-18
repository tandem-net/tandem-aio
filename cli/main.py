"""Convenience entry point so you can run the CLI with `python main.py` during
development. The installed `tandem` command points at tandem_cli.commands:main."""

from tandem_cli.commands import main

if __name__ == "__main__":
    raise SystemExit(main())
