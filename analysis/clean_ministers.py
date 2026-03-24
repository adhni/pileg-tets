#!/usr/bin/env python3
"""Clean the Mentri (1).xlsx workbook into a tidy CSV."""
from __future__ import annotations

import csv
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zipfile import ZipFile

XLSX_PATH = Path('Mentri (1).xlsx')
OUTPUT_PATH = Path('analysis/ministers_cleaned.csv')
SHEET_PATH = 'xl/worksheets/sheet1.xml'

NS_MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_PKG_REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
NS = {'main': NS_MAIN}

CABINET_LABELS = [
    'Kabinet Pembangunan I (1968-1973)',
    'Kabinet Pembangunan II (1973-1978)',
    'Kabinet Pembangunan III (1978-1983)',
    'Kabinet Pembangunan III - Menteri Muda (1978-1983)',
    'Kabinet Pembangunan IV (1983-1988)',
    'Kabinet Pembangunan V (1988-1993)',
    'Kabinet Pembangunan VI (1993-1998)',
    'Kabinet Pembangunan VII (1998)',
    'Kabinet Reformasi Pembangunan (1998-1999)',
    'Kabinet Persatuan Nasional (1999-2001)',
    'Kabinet Gotong Royong (2001-2004)',
    'Kabinet Indonesia Bersatu I (2004-2009)',
    'Kabinet Indonesia Bersatu II (2009-2014)',
    'Kabinet Kerja (2014-2019)',
    'Kabinet Indonesia Maju (2019-2024)',
    'Kabinet Prabowo-Gibran (2024-)',
]

MONTHS_ID = {
    'januari': 1,
    'februari': 2,
    'maret': 3,
    'april': 4,
    'mei': 5,
    'juni': 6,
    'juli': 7,
    'agustus': 8,
    'september': 9,
    'oktober': 10,
    'november': 11,
    'desember': 12,
}

FOOTNOTE_RE = re.compile(r'\[[^\]]*\]')


@dataclass
class Row:
    values: List[str]
    links: List[Optional[str]]


@dataclass
class Record:
    cabinet_index: int
    cabinet_label: str
    group: str
    position_no: str
    position_title: str
    person: str
    start_date: str
    end_date: str
    wikipedia_url: str


def load_shared_strings(zf: ZipFile) -> List[str]:
    try:
        data = zf.read('xl/sharedStrings.xml')
    except KeyError:
        return []
    root = ET.fromstring(data)
    values: List[str] = []
    for si in root.findall('main:si', NS):
        texts = [t.text or '' for t in si.findall('.//main:t', NS)]
        values.append(''.join(texts))
    return values


def col_to_index(cell_ref: str) -> int:
    letters = ''.join(ch for ch in cell_ref if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch.upper()) - 64)
    return idx - 1


def index_to_col(idx: int) -> str:
    result = ''
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def expand_range(cell_range: str) -> List[str]:
    if ':' not in cell_range:
        return [cell_range]
    start, end = cell_range.split(':', 1)
    start_col = col_to_index(start)
    end_col = col_to_index(end)
    start_row = int(''.join(ch for ch in start if ch.isdigit()))
    end_row = int(''.join(ch for ch in end if ch.isdigit()))
    refs = []
    for row in range(start_row, end_row + 1):
        for col in range(start_col, end_col + 1):
            refs.append(f'{index_to_col(col)}{row}')
    return refs


def parse_cell_value(cell, shared_strings: List[str]) -> str:
    cell_type = cell.attrib.get('t')
    value_node = cell.find('main:v', NS)
    if cell_type == 's' and value_node is not None:
        return shared_strings[int(value_node.text)]
    if cell_type == 'b' and value_node is not None:
        return 'TRUE' if value_node.text == '1' else 'FALSE'
    if cell_type == 'inlineStr':
        texts = [t.text or '' for t in cell.findall('.//main:t', NS)]
        return ''.join(texts)
    if value_node is not None:
        return value_node.text or ''
    formula = cell.find('main:f', NS)
    if formula is not None and formula.text:
        return formula.text
    return ''


def build_hyperlink_map(root: ET.Element, zf: ZipFile, sheet_path: str) -> Dict[str, str]:
    hyperlink_map: Dict[str, str] = {}
    links_parent = root.find('main:hyperlinks', NS)
    if links_parent is None:
        return hyperlink_map
    rels: Dict[str, str] = {}
    rel_path = sheet_path.replace('worksheets/', 'worksheets/_rels/') + '.rels'
    try:
        rel_root = ET.fromstring(zf.read(rel_path))
    except KeyError:
        rel_root = None
    if rel_root is not None:
        for rel in rel_root.findall('rel:Relationship', {'rel': NS_PKG_REL}):
            rels[rel.attrib['Id']] = rel.attrib.get('Target', '')
    for hyperlink in links_parent.findall('main:hyperlink', NS):
        ref = hyperlink.attrib.get('ref')
        if not ref:
            continue
        rid = hyperlink.attrib.get(f'{{{NS_REL}}}id')
        url = rels.get(rid, '') if rid else hyperlink.attrib.get('location', '')
        if not url:
            continue
        for single in expand_range(ref):
            hyperlink_map[single] = url
    return hyperlink_map


def extract_rows(root: ET.Element, shared_strings: List[str], hyperlinks: Dict[str, str]) -> List[Row]:
    rows: List[Row] = []
    sheet_data = root.find('main:sheetData', NS)
    if sheet_data is None:
        return rows
    for row in sheet_data.findall('main:row', NS):
        cells: Dict[int, Tuple[str, Optional[str]]] = {}
        for cell in row.findall('main:c', NS):
            ref = cell.attrib.get('r')
            if not ref:
                continue
            idx = col_to_index(ref)
            value = parse_cell_value(cell, shared_strings)
            link = hyperlinks.get(ref)
            cells[idx] = (value, link)
        if not cells:
            rows.append(Row([], []))
            continue
        max_idx = max(cells)
        values = [''] * (max_idx + 1)
        links = [None] * (max_idx + 1)
        for idx, (value, link) in cells.items():
            values[idx] = value or ''
            links[idx] = link
        rows.append(Row(values, links))
    return rows


def clean_text(value: str) -> str:
    if value is None:
        return ''
    text = value.replace('\r', ' ').replace('\n', ' ')
    text = text.replace('\u2013', '-').replace('\u2014', '-').replace('\u2019', "'")
    text = text.replace('\u00a0', ' ')
    text = FOOTNOTE_RE.sub('', text)
    text = text.strip('"')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def clean_header_text(value: str) -> str:
    return clean_text(value).lower()


def is_header_row(cells: List[str]) -> bool:
    if not cells:
        return False
    first = clean_header_text(cells[0])
    return first.startswith('no')


def build_header_map(header_cells: List[str]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for idx, cell in enumerate(header_cells):
        text = clean_header_text(cell)
        if not text:
            continue
        if text.startswith('no'):
            mapping['no'] = idx
        elif text.startswith('jabatan'):
            mapping['position'] = idx
        elif text.startswith('pejabat'):
            mapping.setdefault('person', idx)
        elif 'mulai' in text:
            mapping['start'] = idx
        elif 'selesai' in text:
            mapping['end'] = idx
        elif 'periode' in text:
            mapping['start'] = idx
    if 'start' in mapping and 'end' not in mapping:
        idx = mapping['start']
        mapping['end'] = idx + 1
    return mapping


def clean_number(value: str) -> str:
    if not value:
        return ''
    try:
        as_float = float(value)
        as_int = int(as_float)
        if abs(as_float - as_int) < 1e-6:
            return str(as_int)
        return value
    except ValueError:
        return value


def excel_serial_to_iso(value: float) -> str:
    base = datetime(1899, 12, 30)
    dt = base + timedelta(days=value)
    return dt.date().isoformat()


def parse_date_value(value: str) -> str:
    if not value:
        return ''
    lowered = value.lower()
    if lowered in {'petahana', 'pjs', 'pelaksana tugas'}:
        return value
    try:
        as_float = float(value)
    except ValueError:
        pass
    else:
        return excel_serial_to_iso(as_float)
    parts = value.split(' ')
    if len(parts) >= 3:
        try:
            day = int(parts[0])
            month = MONTHS_ID[parts[1].lower()]
            year = int(parts[2])
            return datetime(year, month, day).date().isoformat()
        except (ValueError, KeyError):
            return value
    return value


def detect_group(cells: List[str], header_map: Dict[str, int]) -> Optional[str]:
    person_idx = header_map.get('person', -1)
    if person_idx >= 0 and person_idx < len(cells) and cells[person_idx]:
        return None
    for text in cells:
        if not text:
            continue
        lowered = text.lower()
        if not lowered.startswith('menteri'):
            continue
        if 'akan diperbantukan' in lowered or 'pada tanggal' in lowered or 'mereka adalah' in lowered:
            continue
        return text
    return None


def normalize_records(rows: List[Row]) -> List[Record]:
    records: List[Record] = []
    cabinet_idx = -1
    header_map: Dict[str, int] = {}
    cabinet_label = ''
    current_group = ''
    current_no = ''
    current_position = ''
    for row in rows:
        if not row.values:
            continue
        cleaned = [clean_text(val) for val in row.values]
        if is_header_row(row.values):
            cabinet_idx += 1
            header_map = build_header_map(row.values)
            cabinet_label = CABINET_LABELS[cabinet_idx] if cabinet_idx < len(CABINET_LABELS) else f'Blok {cabinet_idx + 1}'
            current_group = ''
            current_no = ''
            current_position = ''
            continue
        if not header_map:
            continue
        if not any(cleaned):
            continue
        group = detect_group(cleaned, header_map)
        if group:
            current_group = group
            continue
        person_idx = header_map.get('person')
        start_idx = header_map.get('start')
        end_idx = header_map.get('end')
        pos_idx = header_map.get('position')
        no_idx = header_map.get('no')
        if person_idx is None or person_idx >= len(cleaned):
            continue
        person = cleaned[person_idx]
        if not person:
            continue
        if pos_idx is not None and pos_idx < len(cleaned) and cleaned[pos_idx]:
            current_position = cleaned[pos_idx]
        if no_idx is not None and no_idx < len(cleaned) and cleaned[no_idx]:
            current_no = clean_number(cleaned[no_idx])
        start_raw = cleaned[start_idx] if start_idx is not None and start_idx < len(cleaned) else ''
        end_raw = cleaned[end_idx] if end_idx is not None and end_idx < len(cleaned) else ''
        start_date = parse_date_value(start_raw)
        end_date = parse_date_value(end_raw)
        link = ''
        if person_idx < len(row.links) and row.links[person_idx]:
            link = row.links[person_idx] or ''
        records.append(
            Record(
                cabinet_index=cabinet_idx + 1,
                cabinet_label=cabinet_label,
                group=current_group,
                position_no=current_no,
                position_title=current_position,
                person=person,
                start_date=start_date,
                end_date=end_date,
                wikipedia_url=link,
            )
        )
    return records


def write_csv(records: List[Record], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'cabinet_index',
            'cabinet_label',
            'position_group',
            'position_no',
            'position_title',
            'person',
            'start_date',
            'end_date',
            'wikipedia_url',
        ])
        for record in records:
            writer.writerow([
                record.cabinet_index,
                record.cabinet_label,
                record.group,
                record.position_no,
                record.position_title,
                record.person,
                record.start_date,
                record.end_date,
                record.wikipedia_url,
            ])


def main() -> None:
    if not XLSX_PATH.exists():
        raise SystemExit(f'Missing workbook: {XLSX_PATH}')
    with ZipFile(XLSX_PATH) as zf:
        shared_strings = load_shared_strings(zf)
        sheet_data = zf.read(SHEET_PATH)
        root = ET.fromstring(sheet_data)
        hyperlinks = build_hyperlink_map(root, zf, SHEET_PATH)
        rows = extract_rows(root, shared_strings, hyperlinks)
    records = normalize_records(rows)
    write_csv(records, OUTPUT_PATH)
    print(f'Wrote {OUTPUT_PATH} with {len(records)} rows')


if __name__ == '__main__':
    main()
