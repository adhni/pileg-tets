#!/usr/bin/env python3

"""Enrich ministers_cleaned.csv with birth date and place from Wikipedia/Wikidata."""
from __future__ import annotations


import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, unquote
from urllib.request import Request, urlopen

MINISTERS_PATH = Path('analysis/ministers_cleaned.csv')
OUTPUT_PATH = Path('analysis/ministers_enriched.csv')
CACHE_PATH = Path('analysis/wiki_cache.json')
USER_AGENT = 'CodexCLI-Ministers/1.0 (contact: user@example.com)'
SLEEP_BETWEEN_REQUESTS = 0.1


@dataclass
class EnrichedPerson:
    birth_date: str
    birth_place_id: str
    birth_place_label: str


class Cache:
    def __init__(self, path: Path) -> None:
        self.path = path
        if path.exists():
            try:
                self.data = json.loads(path.read_text())
            except json.JSONDecodeError:
                self.data = {}
        else:
            self.data = {}

    def get(self, key: str) -> Optional[Dict[str, str]]:
        value = self.data.get(key)
        if isinstance(value, dict):
            return value
        return None

    def set(self, key: str, payload: Dict[str, str]) -> None:
        self.data[key] = dict(payload)

    def save(self) -> None:
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
        tmp.replace(self.path)


def fetch_json(url: str, params: Optional[Dict[str, str]] = None) -> Dict:
    if params:
        query = urlencode(params)
        full_url = f'{url}?{query}'
    else:
        full_url = url
    request = Request(full_url, headers={'User-Agent': USER_AGENT})
    with urlopen(request, timeout=30) as resp:
        data = resp.read()
    return json.loads(data.decode('utf-8'))


def title_from_url(url: str) -> Tuple[str, str]:
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f'Invalid URL: {url}')
    if 'wikipedia.org' not in parsed.netloc:
        raise ValueError(f'Unsupported host: {url}')
    lang = parsed.netloc.split('.')[0]
    if not parsed.path.startswith('/wiki/'):
        raise ValueError(f'Unexpected path: {url}')
    title = parsed.path.split('/wiki/', 1)[1]
    title = unquote(title)
    return lang, title.replace(' ', '_')


def fetch_wikidata_id(lang: str, title: str) -> Optional[str]:
    params = {
        'action': 'query',
        'prop': 'pageprops',
        'titles': title,
        'format': 'json',
        'formatversion': '2',
    }
    url = f'https://{lang}.wikipedia.org/w/api.php'
    data = fetch_json(url, params)
    pages = data.get('query', {}).get('pages', [])
    if not pages:
        return None
    page = pages[0]
    props = page.get('pageprops', {})
    return props.get('wikibase_item')


def fetch_entity(qid: str) -> Optional[Dict]:
    url = f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json'
    data = fetch_json(url)
    return data.get('entities', {}).get(qid)


def parse_birth_date(entity: Dict) -> str:
    claims = entity.get('claims', {}).get('P569', [])
    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        if mainsnak.get('snaktype') != 'value':
            continue
        datavalue = mainsnak.get('datavalue', {})
        value = datavalue.get('value', {})
        time_value = value.get('time')
        if not time_value:
            continue
        if time_value.startswith('+') or time_value.startswith('-'):
            time_value = time_value[1:]
        return time_value.split('T', 1)[0]
    return ''


def parse_birth_place_id(entity: Dict) -> str:
    claims = entity.get('claims', {}).get('P19', [])
    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        if mainsnak.get('snaktype') != 'value':
            continue
        datavalue = mainsnak.get('datavalue', {})
        value = datavalue.get('value', {})
        place_id = value.get('id')
        if place_id:
            return place_id
    return ''


def fetch_place_labels(qids: Iterable[str]) -> Dict[str, str]:
    ids = [qid for qid in qids if qid]
    labels: Dict[str, str] = {}
    if not ids:
        return labels
    chunk_size = 50
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i:i + chunk_size]
        params = {
            'action': 'wbgetentities',
            'format': 'json',
            'props': 'labels',
            'languages': 'id|en',
            'ids': '|'.join(chunk),
        }
        data = fetch_json('https://www.wikidata.org/w/api.php', params)
        entities = data.get('entities', {})
        for qid, entity in entities.items():
            label = ''
            labels_dict = entity.get('labels', {})
            for lang in ('id', 'en'):
                if lang in labels_dict:
                    label = labels_dict[lang].get('value', '')
                    if label:
                        break
            labels[qid] = label
        time.sleep(SLEEP_BETWEEN_REQUESTS)
    return labels


def enrich_people(urls: Iterable[str], cache: Cache) -> Dict[str, EnrichedPerson]:
    enriched: Dict[str, EnrichedPerson] = {}
    place_ids: Dict[str, List[str]] = {}
    for url in urls:
        cached = cache.get(url)
        if cached:
            payload = EnrichedPerson(
                birth_date=cached.get('birth_date', ''),
                birth_place_id=cached.get('birth_place_id', ''),
                birth_place_label=cached.get('birth_place_label', ''),
            )
            enriched[url] = payload
            if payload.birth_place_id and not payload.birth_place_label:
                place_ids.setdefault(payload.birth_place_id, []).append(url)
            continue
        try:
            lang, title = title_from_url(url)
            qid = fetch_wikidata_id(lang, title)
            if not qid:
                payload = EnrichedPerson('', '', '')
                enriched[url] = payload
                cache.set(url, payload.__dict__)
                continue
            entity = fetch_entity(qid)
            if not entity:
                payload = EnrichedPerson('', '', '')
                enriched[url] = payload
                cache.set(url, payload.__dict__)
                continue
            birth_date = parse_birth_date(entity)
            birth_place_id = parse_birth_place_id(entity)
            payload = EnrichedPerson(birth_date, birth_place_id, '')
            enriched[url] = payload
            cache.set(url, payload.__dict__)
            if birth_place_id:
                place_ids.setdefault(birth_place_id, []).append(url)
            time.sleep(SLEEP_BETWEEN_REQUESTS)
        except (URLError, HTTPError) as exc:
            raise SystemExit(f'Network error while fetching {url}: {exc}')
    labels = fetch_place_labels(place_ids.keys())
    for place_id, linked_urls in place_ids.items():
        label = labels.get(place_id, '')
        if not label:
            continue
        for url in linked_urls:
            data = enriched[url]
            data.birth_place_label = label
            cached = cache.get(url) or {}
            cached.update({
                'birth_date': data.birth_date,
                'birth_place_id': data.birth_place_id,
                'birth_place_label': data.birth_place_label,
            })
            cache.set(url, cached)
    cache.save()
    return enriched


def load_people(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_enriched(rows: List[Dict[str, str]], enriched: Dict[str, EnrichedPerson], output_path: Path) -> None:
    if not rows:
        raise SystemExit('No rows found in ministers_cleaned.csv')
    fieldnames = list(rows[0].keys()) + ['birth_date', 'birth_place_id', 'birth_place']
    with output_path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            url = row.get('wikipedia_url', '')
            data = enriched.get(url, EnrichedPerson('', '', ''))
            row_out = dict(row)
            row_out['birth_date'] = data.birth_date
            row_out['birth_place_id'] = data.birth_place_id
            row_out['birth_place'] = data.birth_place_label
            writer.writerow(row_out)


def main() -> None:
    if not MINISTERS_PATH.exists():
        raise SystemExit('Run clean_ministers.py first to create ministers_cleaned.csv.')
    rows = load_people(MINISTERS_PATH)
    unique_urls: List[str] = []
    seen: set[str] = set()
    for row in rows:
        url = row.get('wikipedia_url', '').strip()
        if not url or url in seen:
            continue
        seen.add(url)
        unique_urls.append(url)
    cache = Cache(CACHE_PATH)
    enriched = enrich_people(unique_urls, cache)
    write_enriched(rows, enriched, OUTPUT_PATH)
    print(f'Wrote {OUTPUT_PATH} with birth data for {len(enriched)} Wikipedia pages.')


if __name__ == '__main__':
    main()
