#!/usr/bin/env python3
"""
Slimming catalog: which launchd daemons a slim simulator turns off.

The data lives in slim-catalog.json and is ported from simslim
(https://github.com/MobAI-App/simslim, MIT, Copyright (c) 2026 Interlap).
Keeping it as data rather than code means refreshing it against upstream is a
regeneration, not a rewrite.

Two sets matter throughout:

- slimmable labels: every daemon a profile is allowed to disable.
- managed labels: slimmable plus a handful that must stay enabled but that
  older tooling may have disabled. Managed is the mutation allowlist, so a
  daemon outside it is never touched in either direction - that is what keeps
  a stray `launchctl disable` from an unrelated tool from being clobbered.
"""

import json
import os
from typing import Dict, List, Optional, Sequence, Set, Tuple

CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slim-catalog.json')

DEFAULT_PLATFORM = 'ios'

_catalog = None
_platform = DEFAULT_PLATFORM
_views = {}  # type: Dict[str, dict]


class ProfileError(Exception):
    """A profile the user asked for cannot be built (bad category, label, or file)."""


def load_catalog() -> dict:
    """Load and cache slim-catalog.json."""
    global _catalog
    if _catalog is None:
        with open(CATALOG_PATH, 'r', encoding='utf-8') as handle:
            _catalog = json.load(handle)
    return _catalog


def known_platforms() -> List[str]:
    return sorted({DEFAULT_PLATFORM} | set(load_catalog().get('platformExtras', {})))


def select_platform(platform: str) -> None:
    """Bind the catalog to one simulator platform for the rest of the process.

    Every command slims exactly one device, so the platform is resolved once -
    from the device itself - and the catalog answers for it from then on.
    Threading a platform argument through all nine accessors and their callers
    would buy nothing: no run has two platforms in view at once.
    """
    global _platform
    if platform not in known_platforms():
        raise ProfileError('unknown platform "{}" (known: {})'.format(
            platform, ', '.join(known_platforms())))
    _platform = platform


def current_platform() -> str:
    return _platform


def _extras() -> dict:
    """The bound platform's local additions to the upstream data.

    iOS *is* the upstream catalog, so it has no extras; another platform is
    that catalog plus a block of its own. See the `platformExtras` note in
    slim-catalog.json for why the two are kept apart.
    """
    return load_catalog().get('platformExtras', {}).get(_platform, {})


def _merge_labels(base: Sequence[str], added: Sequence[str]) -> List[str]:
    merged = list(base)
    merged.extend(label for label in added if label not in merged)
    return merged


def _view() -> dict:
    """The merged catalog for the bound platform, built once and cached.

    The merge *extends* the upstream categories rather than replacing them, so
    a category ID means the same thing on every platform and a profile written
    against one simulator still validates against another - which is what lets
    a project commit one profile and slim both halves of a paired pair with it.
    """
    if _platform in _views:
        return _views[_platform]

    base = load_catalog()
    extras = _extras()
    extra_labels = extras.get('categories', {})
    extra_features = extras.get('features', {})

    known_ids = {category['id'] for category in base['categories']}
    unknown = sorted(set(extra_labels) - known_ids)
    if unknown:
        raise ProfileError(
            'platformExtras.{}.categories names unknown categories: {}'.format(
                _platform, ', '.join(unknown)))
    known_features = {feature['id'] for feature in base['features']}
    unknown = sorted(set(extra_features) - known_features)
    if unknown:
        raise ProfileError(
            'platformExtras.{}.features names unknown features: {}'.format(
                _platform, ', '.join(unknown)))

    categories_view = []
    for category in base['categories']:
        added = extra_labels.get(category['id'], [])
        if not added:
            categories_view.append(category)
            continue
        merged = dict(category)
        merged['labels'] = _merge_labels(category['labels'], added)
        categories_view.append(merged)

    features_view = []
    for feature in base['features']:
        added = extra_features.get(feature['id'], [])
        if not added:
            features_view.append(feature)
            continue
        merged = dict(feature)
        merged['labels'] = _merge_labels(feature['labels'], added)
        features_view.append(merged)

    descriptions = dict(base['serviceDescriptions'])
    descriptions.update(extras.get('serviceDescriptions', {}))

    _views[_platform] = {
        'categories': categories_view,
        'features': features_view,
        'serviceDescriptions': descriptions,
        'alwaysEnabled': list(extras.get('alwaysEnabled', [])),
    }
    return _views[_platform]


def categories() -> List[dict]:
    return _view()['categories']


def features() -> List[dict]:
    return _view()['features']


def service_descriptions() -> Dict[str, str]:
    return _view()['serviceDescriptions']


def source_info() -> dict:
    return load_catalog()['source']


def describe_service(label: str) -> str:
    return service_descriptions().get(label, '')


def category_by_id(category_id: str) -> Optional[dict]:
    for category in categories():
        if category['id'] == category_id:
            return category
    return None


def feature_by_id(feature_id: str) -> Optional[dict]:
    for feature in features():
        if feature['id'] == feature_id:
            return feature
    return None


def slimmable_labels() -> Set[str]:
    """Every label a profile may disable."""
    labels = set()
    for category in categories():
        labels.update(category['labels'])
    return labels


def managed_labels() -> Set[str]:
    """The mutation allowlist: slimmable labels plus always-enabled ones.

    Always-enabled labels are only ever transitioned back to enabled, which is
    how a simulator slimmed by an older allowlist gets repaired.
    """
    return slimmable_labels() | always_enabled_labels()


def always_enabled_labels() -> Set[str]:
    """Labels that must stay enabled, and are repaired if found disabled.

    Never overlaps the slimmable set, so listing one here is how a daemon a
    platform cannot live without is protected from a future catalog edit:
    `nanoregistryd` on a watch strands the pairing, and an unpaired watch
    simulator is one no companion app installs onto.
    """
    labels = {service['label'] for service in _view()['alwaysEnabled']}
    for category in categories():
        for service in category.get('alwaysEnabled', []):
            labels.add(service['label'])
    return labels


def parse_list(value: Optional[str]) -> List[str]:
    """Split a comma-separated CLI value, tolerating spaces and empty entries."""
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def read_profile_file(path: str) -> Tuple[List[str], List[str], dict]:
    """Read a JSON profile file into (except_ids, keep_labels, metadata).

    Unknown fields are rejected so a typo fails loudly instead of silently
    slimming more than the author intended.
    """
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise ProfileError('profile file not found: {}'.format(path))
    except json.JSONDecodeError as exc:
        raise ProfileError('profile file is not valid JSON: {}'.format(exc))

    if not isinstance(data, dict):
        raise ProfileError('profile file must contain a JSON object')

    allowed = {'name', 'description', 'except', 'keep'}
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ProfileError(
            'unknown field(s) in profile file: {} (allowed: {})'.format(
                ', '.join(unknown), ', '.join(sorted(allowed))))

    for field in ('except', 'keep'):
        if field in data and not isinstance(data[field], list):
            raise ProfileError('profile field "{}" must be a list of strings'.format(field))

    metadata = {
        'name': data.get('name'),
        'description': data.get('description'),
        'path': path,
    }
    return list(data.get('except', [])), list(data.get('keep', [])), metadata


def build_profile(except_ids: Sequence[str] = (), keep_labels: Sequence[str] = (),
                  profile_path: Optional[str] = None) -> dict:
    """Resolve a slimming selection into the exact labels to disable.

    A profile file is the single source of truth for its run, so combining it
    with --except/--keep is rejected rather than silently merged: a CI job and
    a committed profile disagreeing about what "slim" means is exactly the
    drift `verify` exists to catch.
    """
    metadata = {}
    if profile_path:
        if except_ids or keep_labels:
            raise ProfileError('--profile cannot be combined with --except or --keep')
        except_ids, keep_labels, metadata = read_profile_file(profile_path)

    known_ids = {category['id'] for category in categories()}
    unknown_categories = [cid for cid in except_ids if cid not in known_ids]
    if unknown_categories:
        raise ProfileError(
            'unknown category ID(s): {} (known: {})'.format(
                ', '.join(unknown_categories), ', '.join(sorted(known_ids))))

    slimmable = slimmable_labels()
    unknown_labels = [label for label in keep_labels if label not in slimmable]
    if unknown_labels:
        raise ProfileError(
            'no category disables these label(s), so keeping them is a no-op: {}'.format(
                ', '.join(unknown_labels)))

    desired = set(slimmable)
    # Categories share labels, so an excepted category keeps all of its labels
    # enabled even when another slimmed category also lists them.
    for category_id in except_ids:
        desired.difference_update(category_by_id(category_id)['labels'])
    desired.difference_update(keep_labels)

    return {
        'except': sorted(set(except_ids)),
        'keep': sorted(set(keep_labels)),
        'desired': desired,
        'metadata': metadata,
    }


def delta(current: Set[str], desired: Set[str], managed: Set[str]) -> Tuple[List[str], List[str]]:
    """Transitions needed to move `current` to `desired`, scoped to managed labels.

    Anything outside the managed allowlist is left exactly as it is, in both
    directions.
    """
    to_disable = sorted(label for label in desired if label in managed and label not in current)
    to_enable = sorted(label for label in current if label in managed and label not in desired)
    return to_disable, to_enable


def affected_categories(disabled: Set[str]) -> List[dict]:
    """Group disabled labels by category, in catalog order, skipping untouched ones.

    This is what turns "170 daemons are off" into something a person can act
    on: which capabilities they gave up, and what breaks as a result.
    """
    result = []
    for category in categories():
        labels = sorted(label for label in category['labels'] if label in disabled)
        if not labels:
            continue
        result.append({
            'id': category['id'],
            'name': category['name'],
            'downside': category['downside'],
            'disabled_count': len(labels),
            'total_count': len(category['labels']),
            'labels': labels,
        })
    return result


def diagnose_features(feature_ids: Sequence[str], disabled: Set[str]) -> dict:
    """Report, per requested feature, which of its daemons are currently disabled.

    A feature is only OK when every daemon backing it is still running, since a
    half-slimmed capability fails at runtime in ways that look like app bugs.
    """
    statuses = []
    all_ok = True
    for feature_id in feature_ids:
        feature = feature_by_id(feature_id)
        if feature is None:
            known = ', '.join(entry['id'] for entry in features())
            raise ProfileError('unknown feature "{}" (known: {})'.format(feature_id, known))
        down = [label for label in feature['labels'] if label in disabled]
        ok = not down
        all_ok = all_ok and ok
        statuses.append({
            'id': feature['id'],
            'name': feature['name'],
            'ok': ok,
            'disabled': down,
        })
    return {'ok': all_ok, 'features': statuses}
