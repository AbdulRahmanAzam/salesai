from pathlib import Path
import sys
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sales Intelligence Pipeline -- prospecting, research, personalisation, outreach, and tracking agents."
    )
    subparsers = parser.add_subparsers(dest="command")

    from prospecting_agent.cli import add_prospect_subparser, run_prospect_command
    from research_agent.cli import add_research_subparser, run_research_command
    from personalisation_agent.cli import add_personalise_subparser, run_personalise_command
    from outreach_agent.cli import add_outreach_subparser, run_outreach_command
    from tracking_agent.cli import add_tracking_subparser, run_tracking_command

    add_prospect_subparser(subparsers)
    add_research_subparser(subparsers)
    add_personalise_subparser(subparsers)
    add_outreach_subparser(subparsers)
    add_tracking_subparser(subparsers)

    args = parser.parse_args()

    if args.command == "prospect":
        run_prospect_command(args)
    elif args.command == "research":
        run_research_command(args)
    elif args.command == "personalise":
        run_personalise_command(args)
    elif args.command == "outreach":
        run_outreach_command(args)
    elif args.command == "tracking":
        run_tracking_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
