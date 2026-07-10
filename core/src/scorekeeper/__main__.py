"""``python -m scorekeeper`` — used by the async worker spawn (no PATH assumption)."""

from .cli import main

raise SystemExit(main())
