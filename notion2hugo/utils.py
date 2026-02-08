# Python function to convert all symbols to a dashed format
def to_dashed(s):
    dashed = ''.join(['-' if not c.isalnum() else c for c in s]).lower()

    # If there are multiple dashes in a row, reduce to single dash
    while '--' in dashed:
        dashed = dashed.replace('--', '-')

    # Remove leading/trailing dashes
    dashed = dashed.strip('-')

    return dashed
