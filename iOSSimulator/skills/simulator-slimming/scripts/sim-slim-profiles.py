#!/usr/bin/env python3
"""
List what a slim boot turns off.

Run this before slimming when the user needs a capability and you have to work
out which category to keep. Every category names its downside, so the trade-off
is visible without booting anything.

Usage:
    sim-slim-profiles.py
    sim-slim-profiles.py --category siri
    sim-slim-profiles.py --find com.apple.apsd

Options:
    --category <id>  Show the launchd labels in one category, with descriptions
    --find <label>   Show which categories disable a given launchd label

Output:
    JSON object on stdout. Reads no simulator state.
"""

import argparse
import json

import slim_catalog as catalog


def category_summary(category):
    return {
        'id': category['id'],
        'name': category['name'],
        'description': category['description'],
        'downside': category['downside'],
        'approx_memory_mb': category['approxMemoryMB'],
        'label_count': len(category['labels']),
    }


def category_detail(category):
    detail = category_summary(category)
    detail['labels'] = [
        {'label': label, 'purpose': catalog.describe_service(label)}
        for label in category['labels']
    ]
    if category.get('alwaysEnabled'):
        # Shown for transparency: these are in the allowlist only so a
        # simulator slimmed by older tooling can be repaired, never disabled.
        detail['always_enabled'] = [
            {'label': service['label'], 'reason': service['reason']}
            for service in category['alwaysEnabled']
        ]
    return detail


def main():
    parser = argparse.ArgumentParser(description='List simulator slimming categories')
    parser.add_argument('--category', help='Show one category in full')
    parser.add_argument('--find', help='Show which categories disable a launchd label')
    parser.add_argument('--platform', default=catalog.DEFAULT_PLATFORM,
                        choices=catalog.known_platforms(),
                        help='Which platform to describe (default: ios)')
    args = parser.parse_args()

    # The only command with no device to read the platform from, so it is asked
    # for: a watch disables everything below plus its own daemons.
    catalog.select_platform(args.platform)

    if args.category:
        category = catalog.category_by_id(args.category)
        if category is None:
            known = ', '.join(entry['id'] for entry in catalog.categories())
            print(json.dumps({'success': False,
                              'error': 'unknown category "{}" (known: {})'.format(
                                  args.category, known)}))
            raise SystemExit(1)
        print(json.dumps({'success': True, 'category': category_detail(category)}))
        return

    if args.find:
        matches = [category_summary(category) for category in catalog.categories()
                   if args.find in category['labels']]
        print(json.dumps({
            'success': True,
            'label': args.find,
            'purpose': catalog.describe_service(args.find),
            'disabled_by': matches,
            'slimmable': bool(matches),
        }))
        return

    print(json.dumps({
        'success': True,
        'platform': catalog.current_platform(),
        'categories': [category_summary(category) for category in catalog.categories()],
        'slimmable_total': len(catalog.slimmable_labels()),
        'note': ('memory figures are clean-boot medians and are not additive; they rank '
                 'categories rather than predict a total'),
        'source': catalog.source_info(),
    }))


if __name__ == '__main__':
    main()
