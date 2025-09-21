"""Command-line interface for xtgen.

This module provides the command-line argument parsing, validation,
and entry point for the xtgen external generator tool.
"""

import argparse
import sys
from pathlib import Path
from typing import Union

from .templates import Generator, PdProject, MaxProject, get_package_resource_path, OUTPUT_DIR


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    # Import here to check YAML availability from templates module
    from .templates import YAML_AVAILABLE

    # Build description and examples based on YAML availability
    if YAML_AVAILABLE:
        description = "Generate PureData and Max/MSP external projects from YAML or JSON specifications"
        examples = """
Examples:
  %(prog)s counter.yml                    # Generate PD project from YAML
  %(prog)s counter.json                   # Generate PD project from JSON
  %(prog)s -t max counter.yml             # Generate Max/MSP project
  %(prog)s -o /tmp/build counter.yml      # Custom output directory
  %(prog)s -v counter.yml                 # Verbose output
  %(prog)s --list-examples                # List available examples

Supported file formats:
  .yml, .yaml  - YAML specification files
  .json        - JSON specification files"""
    else:
        description = "Generate PureData and Max/MSP external projects from JSON specifications"
        examples = """
Examples:
  %(prog)s counter.json                   # Generate PD project from JSON
  %(prog)s -t max counter.json            # Generate Max/MSP project
  %(prog)s -o /tmp/build counter.json     # Custom output directory
  %(prog)s -v counter.json                # Verbose output
  %(prog)s --list-examples                # List available examples

Supported file formats:
  .json        - JSON specification files

Note: YAML support is not available. Install PyYAML to enable YAML file support:
  pip install PyYAML"""

    parser = argparse.ArgumentParser(
        prog="xtgen",
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples
    )

    # Positional argument for specification file
    parser.add_argument(
        "spec_file",
        nargs="?",
        help="Path to YAML or JSON specification file (default: counter.yml from examples)",
        default=None,
    )

    # Target platform selection
    parser.add_argument(
        "-t",
        "--target",
        choices=["pd", "max"],
        default="pd",
        help="Target platform: 'pd' for PureData, 'max' for Max/MSP (default: pd)",
    )

    # Output directory
    parser.add_argument(
        "-o",
        "--output",
        metavar="DIR",
        default=OUTPUT_DIR,
        help=f"Output directory for generated projects (default: {OUTPUT_DIR})",
    )

    # Verbosity control
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output with detailed generation information",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output except errors",
    )

    # Force overwrite
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force overwrite existing project directory without warning",
    )

    # List examples
    parser.add_argument(
        "--list-examples",
        action="store_true",
        help="List available example specification files and exit",
    )

    # Validate only
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate specification file without generating project",
    )

    return parser


def list_examples() -> None:
    """List available example specification files."""
    examples_dir = get_package_resource_path("resources/examples")
    if not examples_dir.exists():
        print("No examples directory found.")
        return

    print("Available example specification files:")
    print("=====================================")

    for file_path in sorted(examples_dir.glob("*")):
        if file_path.suffix.lower() in [".yml", ".yaml", ".json"]:
            print(f"  {file_path}")

    print("\nUsage: xtgen <example_file>")


def validate_specification(spec_file: Path, verbose: bool = False) -> bool:
    """Validate a specification file without generating output.

    Args:
        spec_file: Path to specification file
        verbose: Enable verbose validation output

    Returns:
        True if validation passes, False otherwise
    """
    try:
        if verbose:
            print(f"Validating specification file: {spec_file}")

        generator = Generator(spec_file)
        spec_data = generator.load_specification()
        generator.validate_specification_structure(spec_data)

        if verbose:
            print("✓ File format valid")
            print("✓ Specification structure valid")
            print("✓ Required fields present")

            # Show basic info about the external
            external_data = spec_data["externals"][0]
            print(f"✓ External name: {external_data['name']}")
            print(f"✓ Namespace: {external_data['namespace']}")
            print(f"✓ Parameters: {len(external_data.get('params', []))}")
            print(f"✓ Outlets: {len(external_data.get('outlets', []))}")
            print(f"✓ Message methods: {len(external_data.get('message_methods', []))}")
            print(f"✓ Type methods: {len(external_data.get('type_methods', []))}")

        print("Specification validation passed successfully.")
        return True

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return False
    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error during validation: {e}", file=sys.stderr)
        return False


def main() -> int:
    """Main entry point for the command-line interface.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    # Handle mutually exclusive verbose/quiet options
    if args.verbose and args.quiet:
        print("Error: --verbose and --quiet options are mutually exclusive", file=sys.stderr)
        return 1

    # Handle special commands
    if args.list_examples:
        list_examples()
        return 0

    # Handle default specification file
    if args.spec_file is None:
        # Use default example file
        default_spec = get_package_resource_path("resources/examples/counter.yml")
        if not default_spec.exists():
            # Fallback to JSON if YAML example not available
            default_spec = get_package_resource_path("resources/examples/counter.json")
        spec_file = default_spec
    else:
        spec_file = Path(args.spec_file)

    if not spec_file.exists():
        print(f"Error: Specification file not found: {spec_file}", file=sys.stderr)
        return 1

    # Handle validation-only mode
    if args.validate:
        return 0 if validate_specification(spec_file, args.verbose) else 1

    try:
        # Create appropriate project generator
        if args.target == "pd":
            project: Union[PdProject, MaxProject] = PdProject(spec_file, target_dir=args.output)
        elif args.target == "max":
            project = MaxProject(spec_file, target_dir=args.output)
        else:
            print(f"Error: Unknown target platform: {args.target}", file=sys.stderr)
            return 1

        # Verbose output
        if args.verbose:
            print(f"Generating {args.target.upper()} project from: {spec_file}")
            print(f"Output directory: {args.output}")
            print(f"Project directory: {project.project_path}")

        # Generate the project
        project.generate()

        # Success message
        if not args.quiet:
            print(f"Successfully generated {args.target.upper()} project: {project.project_path}")
            if args.verbose:
                print("Files created:")
                for file_path in sorted(project.project_path.glob("*")):
                    if file_path.is_file():
                        print(f"  {file_path}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        if not args.force:
            print(f"Error: {e}", file=sys.stderr)
            print("Use --force to overwrite existing directories", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return 0