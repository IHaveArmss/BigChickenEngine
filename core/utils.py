"""Shared utility functions for the BigChicken Engine."""


def normalize_script_names(raw_scripts):
    """Normalize script list from object data to safe, unique script names."""
    if raw_scripts is None:
        return []

    if isinstance(raw_scripts, str):
        parts = raw_scripts.replace('\n', ',').replace(';', ',').split(',')
    else:
        parts = []
        for item in raw_scripts:
            if isinstance(item, str):
                parts.extend(item.replace('\n', ',').replace(';', ',').split(','))

    normalized = []
    seen = set()
    for s in parts:
        name = s.strip().strip('"').strip("'").replace('\\', '/')
        if not name:
            continue
        if name.startswith('scripts/'):
            name = name[8:]
        if name.endswith('.py'):
            name = name[:-3]
        if name and name not in seen:
            seen.add(name)
            normalized.append(name)
    return normalized
