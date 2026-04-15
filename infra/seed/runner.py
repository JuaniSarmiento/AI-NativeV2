"""Seed data runner — discovers and executes seed files in filename order.

Each seed file must expose an async ``seed(session)`` function.
Files are sorted by name so ``01_base_data.py`` runs before ``02_exercises.py``, etc.

Usage:
    python -m infra.seed.runner
    # or via Make:
    make seed
"""
from __future__ import annotations

import asyncio
import importlib
import logging
import pkgutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add backend to sys.path so app.* imports work
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


def _discover_seed_modules() -> list[str]:
    """Find all seed_*.py or NN_*.py files in infra/seed/, sorted by name."""
    seed_dir = Path(__file__).parent
    modules = []

    for info in pkgutil.iter_modules([str(seed_dir)]):
        name = info.name
        # Skip runner and __init__
        if name in ("runner", "__init__"):
            continue
        modules.append(name)

    return sorted(modules)


async def run_seeds() -> None:
    """Execute all seed files inside an AsyncUnitOfWork."""
    from app.shared.db.unit_of_work import AsyncUnitOfWork

    modules = _discover_seed_modules()
    if not modules:
        logger.warning("No seed modules found in infra/seed/.")
        return

    logger.info("Discovered %d seed module(s): %s", len(modules), ", ".join(modules))

    for module_name in modules:
        full_name = f"infra.seed.{module_name}"
        logger.info("Running seed: %s", full_name)

        mod = importlib.import_module(full_name)
        seed_fn = getattr(mod, "seed", None)

        if seed_fn is None:
            logger.warning("Module %s has no seed() function — skipping.", full_name)
            continue

        async with AsyncUnitOfWork() as uow:
            await seed_fn(uow.session)
            await uow.commit()

        logger.info("Seed %s completed.", full_name)

    logger.info("All seeds completed successfully.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_seeds())
