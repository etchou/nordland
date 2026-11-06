"""Independent arithmetic check of the Nordland office table.

Reads the stable source data file and recomputes weighted case totals and denial rates.
This is a case-data consistency check, not statistical inference.
Run: python verify_case.py
"""
from pathlib import Path
import re

source = (Path(__file__).resolve().parent / 'content' / 'Nordland_Case_Record.md').read_text()
rows = []
for line in source.splitlines():
    if not re.match(r'^Office \d+\s*\|', line):
        continue
    parts = [p.strip() for p in line.split('|')]
    if len(parts) != 7:
        raise ValueError(f'Invalid office table row: {line}')
    label, interview, claims, share, denial_m, denial_o, incomplete = parts
    if interview not in ('Yes', 'No'):
        raise ValueError(f'Unexpected interview indicator: {line}')
    rows.append({
        'office': label,
        'interview': interview == 'Yes',
        'claims': int(claims.replace(',', '')),
        'minority_fraction': float(share.rstrip('%')) / 100,
        'denial_minority': float(denial_m.rstrip('%')) / 100,
        'denial_other': float(denial_o.rstrip('%')) / 100,
        'incomplete': float(incomplete.rstrip('%')) / 100,
    })
assert len(rows) == 16, f'Expected 16 offices, found {len(rows)}'
assert sum(r['interview'] for r in rows) == 6, 'Expected six interview offices'

def grouped(items):
    claims = sum(r['claims'] for r in items)
    minority_claims = sum(r['claims'] * r['minority_fraction'] for r in items)
    other_claims = claims - minority_claims
    minority_denials = sum(r['claims'] * r['minority_fraction'] * r['denial_minority'] for r in items)
    other_denials = sum(r['claims'] * (1-r['minority_fraction']) * r['denial_other'] for r in items)
    return {
        'claims': claims,
        'minority_claims': minority_claims,
        'other_claims': other_claims,
        'minority_share': 100 * minority_claims / claims,
        'minority_denial': 100 * minority_denials / minority_claims,
        'other_denial': 100 * other_denials / other_claims,
    }

a = grouped(rows)
b = grouped([r for r in rows if r['interview']])
c = grouped([r for r in rows if not r['interview']])
assert a['claims'] == 150000, a['claims']
print('Full case table:')
print(f'  Claims: {a["claims"]:,}')
print(f'  Minority-background share: {a["minority_share"]:.2f}%')
print(f'  Weighted initial denials: {a["minority_denial"]:.2f}% minority, {a["other_denial"]:.2f}% other')
print('Discretionary-interview offices:')
print(f'  Share of minority claims: {b["minority_claims"] / a["minority_claims"] * 100:.2f}%')
print(f'  Share of other claims: {b["other_claims"] / a["other_claims"] * 100:.2f}%')
print(f'  Weighted denial rates: {b["minority_denial"]:.2f}% minority, {b["other_denial"]:.2f}% other')
print('Document-only offices:')
print(f'  Weighted denial rates: {c["minority_denial"]:.2f}% minority, {c["other_denial"]:.2f}% other')
