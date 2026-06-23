# tracker.py - CLI to manually add/update job applications

import argparse
from sheets_manager import add_application, update_application_status, mark_ghosted_applications
from config import STATUS


def main():
    parser = argparse.ArgumentParser(
        description="Job Application Tracker CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tracker.py add --company Google --role "Software Engineer" --source LinkedIn
  python tracker.py update --company Google --role "Software Engineer" --status "Interview Scheduled"
  python tracker.py ghost
        """
    )
    subparsers = parser.add_subparsers(dest='command')

    # Add application
    add_parser = subparsers.add_parser('add', help='Add a new job application')
    add_parser.add_argument('--company', required=True, help='Company name')
    add_parser.add_argument('--role', required=True, help='Role/position title')
    add_parser.add_argument('--source', default='Manual',
                            choices=['LinkedIn', 'Naukri', 'Indeed', 'Company Website',
                                     'Referral', 'Internshala', 'Unstop', 'Manual', 'Other'])
    add_parser.add_argument('--link', default='', help='Job posting URL')
    add_parser.add_argument('--notes', default='', help='Additional notes')

    # Update status
    upd_parser = subparsers.add_parser('update', help='Update application status')
    upd_parser.add_argument('--company', required=True)
    upd_parser.add_argument('--role', required=True)
    upd_parser.add_argument('--status', required=True,
                            choices=list(STATUS.values()),
                            help='New status for the application')
    upd_parser.add_argument('--notes', default='', help='Notes for this update')

    # Ghost stale applications
    ghost_parser = subparsers.add_parser('ghost',
        help='Auto-mark applications with no response as Ghosted')
    ghost_parser.add_argument('--days', type=int, default=21,
                               help='Days threshold (default: 21)')

    args = parser.parse_args()

    if args.command == 'add':
        success = add_application(
            company=args.company, role=args.role,
            source=args.source, job_link=args.link, notes=args.notes
        )
        if success:
            print(f"Successfully added: {args.company} - {args.role}")
    elif args.command == 'update':
        success = update_application_status(
            company=args.company, role=args.role,
            new_status=args.status, notes=args.notes
        )
        if success:
            print(f"Updated: {args.company} - {args.role} to {args.status}")
    elif args.command == 'ghost':
        print(f"Marking applications older than {args.days} days as Ghosted...")
        mark_ghosted_applications(days_threshold=args.days)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
