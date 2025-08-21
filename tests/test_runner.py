"""
Test runner utilities for managing unit vs integration tests.
"""
import os
import subprocess
import sys
from pathlib import Path


def run_unit_tests():
    """Run only unit tests (fast, no external dependencies)."""
    cmd = [
        sys.executable, "-m", "pytest",
        "-m", "not integration",
        "--cov=backend",
        "--cov-report=term-missing",
        "-v"
    ]
    return subprocess.run(cmd, cwd=Path(__file__).parent.parent)


def run_integration_tests():
    """Run only integration tests (requires database)."""
    # Check if we're in CI or have database available
    if not os.getenv("DATABASE_URL") and not os.getenv("CI"):
        print("⚠️  Integration tests require DATABASE_URL or CI environment")
        print("   Run: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15")
        print("   Then: export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")
        return subprocess.CompletedProcess([], 1)
    
    cmd = [
        sys.executable, "-m", "pytest",
        "-m", "integration",
        "--cov=backend",
        "--cov-report=term-missing",
        "-v"
    ]
    return subprocess.run(cmd, cwd=Path(__file__).parent.parent)


def run_all_tests():
    """Run all tests (unit + integration)."""
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=backend",
        "--cov-report=term-missing",
        "-v"
    ]
    return subprocess.run(cmd, cwd=Path(__file__).parent.parent)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run tests with different configurations")
    parser.add_argument("--type", choices=["unit", "integration", "all"], default="unit",
                       help="Type of tests to run")
    
    args = parser.parse_args()
    
    if args.type == "unit":
        result = run_unit_tests()
    elif args.type == "integration":
        result = run_integration_tests()
    else:
        result = run_all_tests()
    
    sys.exit(result.returncode)
