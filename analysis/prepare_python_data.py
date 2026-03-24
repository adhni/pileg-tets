#!/usr/bin/env python3
"""Build Python-friendly prepared datasets for election analysis."""
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
PREPARED_DIR = ROOT / "data" / "prepared"

DPR_SOURCE = ROOT / "data" / "processed" / "dpr_all.csv"
DPD_SOURCE = ROOT / "data" / "raw" / "dpd_votes.csv"
DPRD_SOURCE = ROOT / "data" / "raw" / "DPRD.csv"
DPRD2_SOURCE = ROOT / "data" / "raw" / "DPRD2.csv"
DAPIL_SEATS_SOURCE = ROOT / "analysis" / "reference" / "dapil_seat_counts.csv"
DAPIL_SEATS_SOURCE_LABEL = "analysis/reference/dapil_seat_counts.csv"


PROVINCE_ALIASES: Dict[str, str] = {
    "ACEH": "Aceh",
    "Aceh": "Aceh",
    "SUMATERA UTARA": "Sumatera Utara",
    "North Sumatra": "Sumatera Utara",
    "SUMATERA BARAT": "Sumatera Barat",
    "West Sumatra": "Sumatera Barat",
    "RIAU": "Riau",
    "Riau": "Riau",
    "KEPULAUAN RIAU": "Kepulauan Riau",
    "Riau Islands": "Kepulauan Riau",
    "JAMBI": "Jambi",
    "Jambi": "Jambi",
    "SUMATERA SELATAN": "Sumatera Selatan",
    "South Sumatra": "Sumatera Selatan",
    "KEPULAUAN BANGKA BELITUNG": "Kepulauan Bangka Belitung",
    "Bangka Belitung": "Kepulauan Bangka Belitung",
    "BENGKULU": "Bengkulu",
    "Bengkulu": "Bengkulu",
    "LAMPUNG": "Lampung",
    "Lampung": "Lampung",
    "DKI JAKARTA": "DKI Jakarta",
    "Jakarta": "DKI Jakarta",
    "JAWA BARAT": "Jawa Barat",
    "West Java": "Jawa Barat",
    "JAWA TENGAH": "Jawa Tengah",
    "Central Java": "Jawa Tengah",
    "JAWA TIMUR": "Jawa Timur",
    "East Java": "Jawa Timur",
    "DAERAH ISTIMEWA YOGYAKARTA": "Daerah Istimewa Yogyakarta",
    "Yogyakarta": "Daerah Istimewa Yogyakarta",
    "BANTEN": "Banten",
    "Banten": "Banten",
    "BALI": "Bali",
    "Bali": "Bali",
    "NUSA TENGGARA BARAT": "Nusa Tenggara Barat",
    "West Nusa Tenggara": "Nusa Tenggara Barat",
    "NUSA TENGGARA TIMUR": "Nusa Tenggara Timur",
    "East Nusa Tenggara": "Nusa Tenggara Timur",
    "KALIMANTAN BARAT": "Kalimantan Barat",
    "West Kalimantan": "Kalimantan Barat",
    "KALIMANTAN TENGAH": "Kalimantan Tengah",
    "Central Kalimantan": "Kalimantan Tengah",
    "KALIMANTAN SELATAN": "Kalimantan Selatan",
    "South Kalimantan": "Kalimantan Selatan",
    "KALIMANTAN TIMUR": "Kalimantan Timur",
    "KALIMANTAN TMUR": "Kalimantan Timur",
    "East Kalimantan": "Kalimantan Timur",
    "KALIMANTAN UTARA": "Kalimantan Utara",
    "North Kalimantan": "Kalimantan Utara",
    "SULAWESI UTARA": "Sulawesi Utara",
    "North Sulawesi": "Sulawesi Utara",
    "GORONTALO": "Gorontalo",
    "Gorontalo": "Gorontalo",
    "SULAWESI TENGAH": "Sulawesi Tengah",
    "Central Sulawesi": "Sulawesi Tengah",
    "SULAWESI SELATAN": "Sulawesi Selatan",
    "South Sulawesi": "Sulawesi Selatan",
    "SULAWESI BARAT": "Sulawesi Barat",
    "West Sulawesi": "Sulawesi Barat",
    "SULAWESI TENGGARA": "Sulawesi Tenggara",
    "Southeast Sulawesi": "Sulawesi Tenggara",
    "MALUKU": "Maluku",
    "Maluku": "Maluku",
    "MALUKU UTARA": "Maluku Utara",
    "North Maluku": "Maluku Utara",
    "PAPUA": "Papua",
    "P A P U A": "Papua",
    "Papua": "Papua",
    "PAPUA BARAT": "Papua Barat",
    "West Papua": "Papua Barat",
    "PAPUA SELATAN": "Papua Selatan",
    "South Papua": "Papua Selatan",
    "PAPUA TENGAH": "Papua Tengah",
    "Central Papua": "Papua Tengah",
    "PAPUA PEGUNUNGAN": "Papua Pegunungan",
    "Highland Papua": "Papua Pegunungan",
    "PAPUA BARAT DAYA": "Papua Barat Daya",
    "Southwest Papua": "Papua Barat Daya",
}

PROVINCE_ORDER = [
    "Aceh",
    "Sumatera Utara",
    "Sumatera Barat",
    "Riau",
    "Kepulauan Riau",
    "Jambi",
    "Sumatera Selatan",
    "Kepulauan Bangka Belitung",
    "Bengkulu",
    "Lampung",
    "DKI Jakarta",
    "Jawa Barat",
    "Jawa Tengah",
    "Daerah Istimewa Yogyakarta",
    "Jawa Timur",
    "Banten",
    "Bali",
    "Nusa Tenggara Barat",
    "Nusa Tenggara Timur",
    "Kalimantan Barat",
    "Kalimantan Tengah",
    "Kalimantan Selatan",
    "Kalimantan Timur",
    "Kalimantan Utara",
    "Sulawesi Utara",
    "Gorontalo",
    "Sulawesi Tengah",
    "Sulawesi Selatan",
    "Sulawesi Barat",
    "Sulawesi Tenggara",
    "Maluku",
    "Maluku Utara",
    "Papua",
    "Papua Barat",
    "Papua Selatan",
    "Papua Tengah",
    "Papua Pegunungan",
    "Papua Barat Daya",
]

PARTY_ORDER = [
    "PKB",
    "Gerindra",
    "PDIP",
    "Golkar",
    "NasDem",
    "Buruh",
    "Gelora",
    "PKS",
    "PKN",
    "Hanura",
    "Garuda",
    "PAN",
    "PBB",
    "Demokrat",
    "PSI",
    "Perindo",
    "PPP",
    "PNA",
    "Gabthat",
    "PDA",
    "PA",
    "PASA",
    "SIRA",
    "Ummat",
]

PARTY_CODE_TO_NAME = {
    "PKB": "Partai Kebangkitan Bangsa",
    "Gerindra": "Partai Gerakan Indonesia Raya",
    "PDIP": "Partai Demokrasi Indonesia Perjuangan",
    "Golkar": "Partai Golongan Karya",
    "NasDem": "Partai NasDem",
    "Buruh": "Partai Buruh",
    "Gelora": "Partai Gelombang Rakyat Indonesia",
    "PKS": "Partai Keadilan Sejahtera",
    "PKN": "Partai Kebangkitan Nusantara",
    "Hanura": "Partai Hati Nurani Rakyat",
    "Garuda": "Partai Garda Republik Indonesia",
    "PAN": "Partai Amanat Nasional",
    "PBB": "Partai Bulan Bintang",
    "Demokrat": "Partai Demokrat",
    "PSI": "Partai Solidaritas Indonesia",
    "Perindo": "Partai Perindo",
    "PPP": "Partai Persatuan Pembangunan",
    "PNA": "PNA",
    "Gabthat": "Gabthat",
    "PDA": "PDA",
    "PA": "PA",
    "PASA": "PASA",
    "SIRA": "SIRA",
    "Ummat": "Partai Ummat",
}

PARTY_NAME_TO_CODE = {
    "Partai Kebangkitan Bangsa": "PKB",
    "Partai Gerakan Indonesia Raya": "Gerindra",
    "Partai Demokrasi Indonesia Perjuangan": "PDIP",
    "Partai Golongan Karya": "Golkar",
    "Partai NasDem": "NasDem",
    "Partai Buruh": "Buruh",
    "Partai Gelombang Rakyat Indonesia": "Gelora",
    "Partai Keadilan Sejahtera": "PKS",
    "Partai Kebangkitan Nusantara": "PKN",
    "Partai Hati Nurani Rakyat": "Hanura",
    "Partai Garda Republik Indonesia": "Garuda",
    "Partai Amanat Nasional": "PAN",
    "Partai Bulan Bintang": "PBB",
    "Partai Demokrat": "Demokrat",
    "Partai Solidaritas Indonesia": "PSI",
    "PARTAI PERINDO": "Perindo",
    "Partai Perindo": "Perindo",
    "Partai Persatuan Pembangunan": "PPP",
    "Partai Ummat": "Ummat",
}

PARTY_SCOPE = {
    "PKB": "national",
    "Gerindra": "national",
    "PDIP": "national",
    "Golkar": "national",
    "NasDem": "national",
    "Buruh": "national",
    "Gelora": "national",
    "PKS": "national",
    "PKN": "national",
    "Hanura": "national",
    "Garuda": "national",
    "PAN": "national",
    "PBB": "national",
    "Demokrat": "national",
    "PSI": "national",
    "Perindo": "national",
    "PPP": "national",
    "PNA": "local_aceh",
    "Gabthat": "local_aceh",
    "PDA": "local_aceh",
    "PA": "local_aceh",
    "PASA": "local_aceh",
    "SIRA": "local_aceh",
    "Ummat": "national",
}

PARTY_LOGOS = {
    "PKB": "assets/logos/PKB.svg",
    "Gerindra": "assets/logos/Gerindra.svg",
    "PDIP": "assets/logos/PDI_P.svg",
    "Golkar": "assets/logos/Golkar.svg",
    "NasDem": "assets/logos/NasDem.png",
    "Buruh": "assets/logos/Buruh.svg",
    "Gelora": "assets/logos/Gelora.png",
    "PKS": "assets/logos/PKS.svg",
    "PKN": "assets/logos/PKN.svg",
    "Hanura": "assets/logos/Hanura.svg",
    "Garuda": "assets/logos/Garuda.png",
    "PAN": "assets/logos/PAN.svg",
    "PBB": "assets/logos/PBB.svg",
    "Demokrat": "assets/logos/Demokrat.svg",
    "PSI": "assets/logos/PSI.svg",
    "Perindo": "assets/logos/Perindo.png",
    "PPP": "assets/logos/PPP.svg",
    "Ummat": "assets/logos/Ummat.svg",
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def parse_int(value: str) -> int:
    return int(str(value).strip().replace(",", ""))


def format_ratio(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def province_sort_key(province: str) -> Tuple[int, str]:
    try:
        return (PROVINCE_ORDER.index(province), province)
    except ValueError:
        return (len(PROVINCE_ORDER), province)


def party_sort_key(code: str) -> Tuple[int, str]:
    try:
        return (PARTY_ORDER.index(code), code)
    except ValueError:
        return (len(PARTY_ORDER), code)


def canonical_province(raw_value: str) -> str:
    key = normalize_space(raw_value)
    if key not in PROVINCE_ALIASES:
        raise KeyError(f"Unknown province alias: {raw_value!r}")
    return PROVINCE_ALIASES[key]


def canonical_party_from_name(raw_name: str) -> Tuple[str, str]:
    key = normalize_space(raw_name)
    if key not in PARTY_NAME_TO_CODE:
        raise KeyError(f"Unknown party name: {raw_name!r}")
    code = PARTY_NAME_TO_CODE[key]
    return code, PARTY_CODE_TO_NAME[code]


def canonical_party_from_code(raw_code: str) -> Tuple[str, str]:
    code = normalize_space(raw_code)
    if code not in PARTY_CODE_TO_NAME:
        raise KeyError(f"Unknown party code: {raw_code!r}")
    return code, PARTY_CODE_TO_NAME[code]


def write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build_party_lookup() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for code in sorted(PARTY_CODE_TO_NAME, key=party_sort_key):
        logo_path = PARTY_LOGOS.get(code, "")
        rows.append(
            {
                "party_code": code,
                "party_name": PARTY_CODE_TO_NAME[code],
                "party_scope": PARTY_SCOPE.get(code, ""),
                "logo_path": logo_path,
            }
        )
    return rows


def build_province_lookup() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    source_rows = [
        ("dpr_all.csv", sorted({row["Province"] for row in load_csv_rows(DPR_SOURCE)})),
        ("dpd_votes.csv", sorted({row["Province"] for row in load_csv_rows(DPD_SOURCE)})),
        ("DPRD.csv", sorted({row["Province"] for row in load_csv_rows(DPRD_SOURCE)})),
        ("DPRD2.csv", sorted({row["Province"] for row in load_csv_rows(DPRD2_SOURCE)})),
    ]
    for source_name, provinces in source_rows:
        for raw_value in provinces:
            if raw_value == "Total seats":
                continue
            rows.append(
                {
                    "source_dataset": source_name,
                    "province_raw": raw_value,
                    "province": canonical_province(raw_value),
                }
            )
    rows.sort(key=lambda item: (province_sort_key(item["province"]), item["source_dataset"], item["province_raw"]))
    return rows


def prepare_dpr_candidates() -> Tuple[List[Dict[str, object]], List[Dict[str, object]], Dict[str, str]]:
    rows = load_csv_rows(DPR_SOURCE)
    prepared_rows: List[Dict[str, object]] = []
    district_to_province: Dict[str, str] = {}
    slates: Dict[Tuple[str, str, str, str], Dict[str, object]] = {}

    for row in rows:
        province_raw = normalize_space(row["Province"])
        province = canonical_province(province_raw)
        district = normalize_space(row["District"])
        party_code, party_name = canonical_party_from_name(row["PartyName"])
        party_vote = parse_int(row["PartyVote"])
        candidate_vote = parse_int(row["CandidateVote"])
        party_number = parse_int(row["PartyNumber"])
        candidate_number = parse_int(row["CandidateNumber"])
        candidate_rank = parse_int(row["CandidateRank"])

        if district in district_to_province and district_to_province[district] != province:
            raise ValueError(f"District {district!r} maps to multiple provinces")
        district_to_province[district] = province

        prepared_rows.append(
            {
                "province": province,
                "province_raw": province_raw,
                "district": district,
                "party_number": party_number,
                "party_code": party_code,
                "party_name": party_name,
                "party_vote": party_vote,
                "candidate_number": candidate_number,
                "candidate_name": normalize_space(row["CandidateName"]),
                "candidate_vote": candidate_vote,
                "candidate_rank": candidate_rank,
                "candidate_rank_raw": normalize_space(row["CandidateRankRaw"]),
            }
        )

        slate_key = (province, district, str(party_number), party_code)
        slate = slates.setdefault(
            slate_key,
            {
                "province": province,
                "district": district,
                "party_number": party_number,
                "party_code": party_code,
                "party_name": party_name,
                "party_vote": party_vote,
                "candidate_count": 0,
                "candidate_vote_total": 0,
                "top_candidate_name": "",
                "top_candidate_vote": -1,
            },
        )
        existing_party_vote = int(slate["party_vote"])
        if existing_party_vote != party_vote:
            raise ValueError(f"Slate {slate_key!r} has inconsistent party votes")
        slate["candidate_count"] = int(slate["candidate_count"]) + 1
        slate["candidate_vote_total"] = int(slate["candidate_vote_total"]) + candidate_vote
        if candidate_vote > int(slate["top_candidate_vote"]):
            slate["top_candidate_vote"] = candidate_vote
            slate["top_candidate_name"] = normalize_space(row["CandidateName"])

    prepared_rows.sort(
        key=lambda item: (
            province_sort_key(str(item["province"])),
            str(item["district"]),
            int(item["party_number"]),
            int(item["candidate_rank"]),
            str(item["candidate_name"]),
        )
    )

    slate_rows: List[Dict[str, object]] = []
    for key in sorted(slates, key=lambda item: (province_sort_key(item[0]), item[1], int(item[2]), party_sort_key(item[3]))):
        slate = slates[key]
        candidate_vote_total = int(slate["candidate_vote_total"])
        party_vote = int(slate["party_vote"])
        total_votes = party_vote + candidate_vote_total
        top_candidate_vote = int(slate["top_candidate_vote"])
        top_share = (top_candidate_vote / candidate_vote_total) if candidate_vote_total else None
        party_vote_share = (party_vote / total_votes) if total_votes else None
        slate_rows.append(
            {
                "province": slate["province"],
                "district": slate["district"],
                "party_number": slate["party_number"],
                "party_code": slate["party_code"],
                "party_name": slate["party_name"],
                "party_vote": party_vote,
                "candidate_count": slate["candidate_count"],
                "candidate_vote_total": candidate_vote_total,
                "total_votes": total_votes,
                "top_candidate_name": slate["top_candidate_name"],
                "top_candidate_vote": top_candidate_vote,
                "top_candidate_vote_share": format_ratio(top_share),
                "party_vote_share": format_ratio(party_vote_share),
            }
        )

    return prepared_rows, slate_rows, district_to_province


def prepare_dpd_candidates() -> List[Dict[str, object]]:
    rows = load_csv_rows(DPD_SOURCE)
    prepared_rows: List[Dict[str, object]] = []
    for row in rows:
        province_raw = normalize_space(row["Province"])
        prepared_rows.append(
            {
                "province": canonical_province(province_raw),
                "province_raw": province_raw,
                "candidate_name": normalize_space(row["Candidate Name"]),
                "vote_count": parse_int(row["Vote Count"]),
                "rank": parse_int(row["Rank"]),
            }
        )
    prepared_rows.sort(
        key=lambda item: (
            province_sort_key(str(item["province"])),
            int(item["rank"]),
            str(item["candidate_name"]),
        )
    )
    return prepared_rows


def prepare_dprd_long(
    raw_path: Path, seat_column_name: str
) -> Tuple[List[Dict[str, object]], Dict[str, int], int, Dict[str, int]]:
    rows = load_csv_rows(raw_path)
    if not rows:
        raise ValueError(f"No rows found in {raw_path}")

    party_codes = [column for column in rows[0].keys() if column not in {"Province", "Total"}]
    totals_row = None
    long_rows: List[Dict[str, object]] = []
    party_totals = Counter()

    for row in rows:
        province_raw = normalize_space(row["Province"])
        if province_raw == "Total seats":
            totals_row = row
            continue

        province = canonical_province(province_raw)
        row_total = 0
        for raw_code in party_codes:
            party_code, party_name = canonical_party_from_code(raw_code)
            seat_count = parse_int(row[raw_code])
            row_total += seat_count
            party_totals[party_code] += seat_count
            long_rows.append(
                {
                    "province": province,
                    "province_raw": province_raw,
                    "party_code": party_code,
                    "party_name": party_name,
                    seat_column_name: seat_count,
                }
            )
        expected_total = parse_int(row["Total"])
        if row_total != expected_total:
            raise ValueError(f"{raw_path.name} row total mismatch for {province_raw}: {row_total} != {expected_total}")

    if totals_row is None:
        raise ValueError(f"Missing Total seats row in {raw_path}")

    source_grand_total = parse_int(totals_row["Total"])
    computed_grand_total = sum(party_totals.values())
    if computed_grand_total != source_grand_total:
        raise ValueError(f"{raw_path.name} total mismatch: {computed_grand_total} != {source_grand_total}")

    long_rows.sort(key=lambda item: (province_sort_key(str(item["province"])), party_sort_key(str(item["party_code"]))))
    reported_totals = {}
    for raw_code in party_codes:
        party_code, _party_name = canonical_party_from_code(raw_code)
        reported_totals[party_code] = parse_int(totals_row[raw_code])
    return long_rows, dict(party_totals), source_grand_total, reported_totals


def prepare_dprd_ratios(
    provincial_rows: List[Dict[str, object]],
    kabkot_rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    provincial_map = {(row["province"], row["party_code"]): int(row["provincial_seats"]) for row in provincial_rows}
    kabkot_map = {(row["province"], row["party_code"]): int(row["kabkot_seats"]) for row in kabkot_rows}
    provinces = sorted({row["province"] for row in provincial_rows} | {row["province"] for row in kabkot_rows}, key=province_sort_key)
    party_codes = sorted(set(PARTY_CODE_TO_NAME), key=party_sort_key)

    ratio_rows: List[Dict[str, object]] = []
    for province in provinces:
        for code in party_codes:
            provincial = provincial_map.get((province, code), 0)
            kabkot = kabkot_map.get((province, code), 0)
            ratio = None
            ratio_defined = "false"
            if provincial > 0:
                ratio = kabkot / provincial
                ratio_defined = "true"
            ratio_rows.append(
                {
                    "province": province,
                    "party_code": code,
                    "party_name": PARTY_CODE_TO_NAME[code],
                    "provincial_seats": provincial,
                    "kabkot_seats": kabkot,
                    "kabkot_to_provincial_ratio": format_ratio(ratio),
                    "ratio_defined": ratio_defined,
                }
            )
    return ratio_rows


def prepare_dprd_totals(
    provincial_totals: Dict[str, int],
    provincial_reported_totals: Dict[str, int],
    kabkot_totals: Dict[str, int],
    kabkot_reported_totals: Dict[str, int],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for code in sorted(set(PARTY_CODE_TO_NAME), key=party_sort_key):
        provincial = provincial_totals.get(code, 0)
        kabkot = kabkot_totals.get(code, 0)
        ratio = kabkot / provincial if provincial else None
        provincial_reported = provincial_reported_totals.get(code, 0)
        kabkot_reported = kabkot_reported_totals.get(code, 0)
        rows.append(
            {
                "party_code": code,
                "party_name": PARTY_CODE_TO_NAME[code],
                "provincial_seats": provincial,
                "provincial_seats_total_row": provincial_reported,
                "provincial_total_matches": "true" if provincial == provincial_reported else "false",
                "kabkot_seats": kabkot,
                "kabkot_seats_total_row": kabkot_reported,
                "kabkot_total_matches": "true" if kabkot == kabkot_reported else "false",
                "kabkot_to_provincial_ratio": format_ratio(ratio),
                "ratio_defined": "true" if provincial else "false",
            }
        )
    return rows


def prepare_dapil_seats(district_to_province: Dict[str, str]) -> List[Dict[str, object]]:
    prepared_rows: List[Dict[str, object]] = []
    seen_districts = set()

    for row in load_csv_rows(DAPIL_SEATS_SOURCE):
        province = normalize_space(row["province"])
        district = normalize_space(row["district"])
        district_label = normalize_space(row["district_label"])
        seat_count = parse_int(row["seat_count"])

        if district in seen_districts:
            raise ValueError(f"Duplicate dapil seat row for district {district!r}")
        if district not in district_to_province:
            raise KeyError(f"Could not match district {district!r} from {DAPIL_SEATS_SOURCE_LABEL}")
        if district_to_province[district] != province:
            raise ValueError(
                f"Seat source province mismatch for {district!r}: {province!r} != {district_to_province[district]!r}"
            )

        seen_districts.add(district)
        prepared_rows.append(
            {
                "province": province,
                "district": district,
                "district_label": district_label,
                "seat_count": seat_count,
                "source_file": DAPIL_SEATS_SOURCE_LABEL,
            }
        )

    missing_districts = sorted(set(district_to_province) - seen_districts)
    if missing_districts:
        raise ValueError(f"Missing dapil seat rows for districts: {', '.join(missing_districts)}")

    prepared_rows.sort(key=lambda item: (province_sort_key(str(item["province"])), str(item["district"])))
    return prepared_rows


def write_data_dictionary(metadata: List[Dict[str, object]], notes: List[str]) -> None:
    lines = [
        "# Prepared Data",
        "",
        "Generated by `analysis/prepare_python_data.py`.",
        "",
        "These files are the Python-first prep layer for the repo. Legacy R/Quarto notebooks are archived under `archive/r_reference/`; the outputs below are normalized and ready for Python analyses.",
        "",
        "## Files",
        "",
    ]

    for item in metadata:
        lines.append(f"### `{item['filename']}`")
        lines.append("")
        lines.append(f"- Purpose: {item['purpose']}")
        lines.append(f"- Source: {item['source']}")
        lines.append(f"- Rows: {item['rows']}")
        lines.append(f"- Columns: {', '.join(item['columns'])}")
        extra = item.get("extra")
        if extra:
            lines.append(f"- Notes: {extra}")
        lines.append("")

    lines.extend(["## Notes", ""])
    for note in notes:
        lines.append(f"- {note}")
    lines.append("")

    output_path = PREPARED_DIR / "DATA_DICTIONARY.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    PREPARED_DIR.mkdir(parents=True, exist_ok=True)

    party_lookup_rows = build_party_lookup()
    province_lookup_rows = build_province_lookup()
    dpr_candidate_rows, dpr_slate_rows, district_to_province = prepare_dpr_candidates()
    dpd_candidate_rows = prepare_dpd_candidates()
    provincial_rows, provincial_totals, provincial_grand_total, provincial_reported_totals = prepare_dprd_long(
        DPRD_SOURCE, "provincial_seats"
    )
    kabkot_rows, kabkot_totals, kabkot_grand_total, kabkot_reported_totals = prepare_dprd_long(
        DPRD2_SOURCE, "kabkot_seats"
    )
    dprd_ratio_rows = prepare_dprd_ratios(provincial_rows, kabkot_rows)
    dprd_total_rows = prepare_dprd_totals(
        provincial_totals,
        provincial_reported_totals,
        kabkot_totals,
        kabkot_reported_totals,
    )
    dapil_seat_rows = prepare_dapil_seats(district_to_province)

    output_counts = {
        "party_lookup.csv": write_csv(
            PREPARED_DIR / "party_lookup.csv",
            ["party_code", "party_name", "party_scope", "logo_path"],
            party_lookup_rows,
        ),
        "province_lookup.csv": write_csv(
            PREPARED_DIR / "province_lookup.csv",
            ["source_dataset", "province_raw", "province"],
            province_lookup_rows,
        ),
        "dpr_candidates_standardized.csv": write_csv(
            PREPARED_DIR / "dpr_candidates_standardized.csv",
            [
                "province",
                "province_raw",
                "district",
                "party_number",
                "party_code",
                "party_name",
                "party_vote",
                "candidate_number",
                "candidate_name",
                "candidate_vote",
                "candidate_rank",
                "candidate_rank_raw",
            ],
            dpr_candidate_rows,
        ),
        "dpr_party_slates.csv": write_csv(
            PREPARED_DIR / "dpr_party_slates.csv",
            [
                "province",
                "district",
                "party_number",
                "party_code",
                "party_name",
                "party_vote",
                "candidate_count",
                "candidate_vote_total",
                "total_votes",
                "top_candidate_name",
                "top_candidate_vote",
                "top_candidate_vote_share",
                "party_vote_share",
            ],
            dpr_slate_rows,
        ),
        "dpd_candidates_standardized.csv": write_csv(
            PREPARED_DIR / "dpd_candidates_standardized.csv",
            ["province", "province_raw", "candidate_name", "vote_count", "rank"],
            dpd_candidate_rows,
        ),
        "dprd_provincial_seats.csv": write_csv(
            PREPARED_DIR / "dprd_provincial_seats.csv",
            ["province", "province_raw", "party_code", "party_name", "provincial_seats"],
            provincial_rows,
        ),
        "dprd_kabkot_seats.csv": write_csv(
            PREPARED_DIR / "dprd_kabkot_seats.csv",
            ["province", "province_raw", "party_code", "party_name", "kabkot_seats"],
            kabkot_rows,
        ),
        "dprd_seat_ratios.csv": write_csv(
            PREPARED_DIR / "dprd_seat_ratios.csv",
            [
                "province",
                "party_code",
                "party_name",
                "provincial_seats",
                "kabkot_seats",
                "kabkot_to_provincial_ratio",
                "ratio_defined",
            ],
            dprd_ratio_rows,
        ),
        "dprd_seat_totals.csv": write_csv(
            PREPARED_DIR / "dprd_seat_totals.csv",
            [
                "party_code",
                "party_name",
                "provincial_seats",
                "provincial_seats_total_row",
                "provincial_total_matches",
                "kabkot_seats",
                "kabkot_seats_total_row",
                "kabkot_total_matches",
                "kabkot_to_provincial_ratio",
                "ratio_defined",
            ],
            dprd_total_rows,
        ),
        "dapil_seats.csv": write_csv(
            PREPARED_DIR / "dapil_seats.csv",
            ["province", "district", "district_label", "seat_count", "source_file"],
            dapil_seat_rows,
        ),
    }

    dprd2_provinces = {row["province"] for row in kabkot_rows}
    dpd_provinces = {row["province"] for row in dpd_candidate_rows}
    all_provinces = {row["province"] for row in dpr_candidate_rows}
    provincial_total_mismatches = [
        code
        for code in sorted(PARTY_CODE_TO_NAME, key=party_sort_key)
        if provincial_totals.get(code, 0) != provincial_reported_totals.get(code, 0)
    ]

    metadata = [
        {
            "filename": "party_lookup.csv",
            "purpose": "Canonical party codes, names, scope, and logo paths.",
            "source": "Repo party names and asset file names.",
            "rows": output_counts["party_lookup.csv"],
            "columns": ["party_code", "party_name", "party_scope", "logo_path"],
        },
        {
            "filename": "province_lookup.csv",
            "purpose": "Observed province-name variants mapped to one canonical province field.",
            "source": "dpr_all.csv, dpd_votes.csv, DPRD.csv, DPRD2.csv.",
            "rows": output_counts["province_lookup.csv"],
            "columns": ["source_dataset", "province_raw", "province"],
        },
        {
            "filename": "dpr_candidates_standardized.csv",
            "purpose": "Canonical candidate-level DPR table for Python analysis.",
            "source": "data/processed/dpr_all.csv.",
            "rows": output_counts["dpr_candidates_standardized.csv"],
            "columns": [
                "province",
                "province_raw",
                "district",
                "party_number",
                "party_code",
                "party_name",
                "party_vote",
                "candidate_number",
                "candidate_name",
                "candidate_vote",
                "candidate_rank",
                "candidate_rank_raw",
            ],
            "extra": "38 provinces, 84 districts, and 1,509 party slates after normalization.",
        },
        {
            "filename": "dpr_party_slates.csv",
            "purpose": "Aggregated per-slate DPR metrics used by several existing notebooks.",
            "source": "Derived from dpr_candidates_standardized.csv.",
            "rows": output_counts["dpr_party_slates.csv"],
            "columns": [
                "province",
                "district",
                "party_number",
                "party_code",
                "party_name",
                "party_vote",
                "candidate_count",
                "candidate_vote_total",
                "total_votes",
                "top_candidate_name",
                "top_candidate_vote",
                "top_candidate_vote_share",
                "party_vote_share",
            ],
        },
        {
            "filename": "dpd_candidates_standardized.csv",
            "purpose": "Canonical candidate-level DPD vote table.",
            "source": "data/raw/dpd_votes.csv.",
            "rows": output_counts["dpd_candidates_standardized.csv"],
            "columns": ["province", "province_raw", "candidate_name", "vote_count", "rank"],
            "extra": "Covers 37 provinces in the source data.",
        },
        {
            "filename": "dprd_provincial_seats.csv",
            "purpose": "Long-form provincial DPRD seat counts without the aggregate Total seats row.",
            "source": "data/raw/DPRD.csv.",
            "rows": output_counts["dprd_provincial_seats.csv"],
            "columns": ["province", "province_raw", "party_code", "party_name", "provincial_seats"],
            "extra": f"Grand total seats preserved separately: {provincial_grand_total}.",
        },
        {
            "filename": "dprd_kabkot_seats.csv",
            "purpose": "Long-form kabupaten/kota DPRD seat counts without the aggregate Total seats row.",
            "source": "data/raw/DPRD2.csv.",
            "rows": output_counts["dprd_kabkot_seats.csv"],
            "columns": ["province", "province_raw", "party_code", "party_name", "kabkot_seats"],
            "extra": f"Grand total seats preserved separately: {kabkot_grand_total}.",
        },
        {
            "filename": "dprd_seat_ratios.csv",
            "purpose": "Province-by-party kabupaten/kota to provincial seat ratios with undefined cases left blank.",
            "source": "Derived from dprd_provincial_seats.csv and dprd_kabkot_seats.csv.",
            "rows": output_counts["dprd_seat_ratios.csv"],
            "columns": [
                "province",
                "party_code",
                "party_name",
                "provincial_seats",
                "kabkot_seats",
                "kabkot_to_provincial_ratio",
                "ratio_defined",
            ],
        },
        {
            "filename": "dprd_seat_totals.csv",
            "purpose": "National party totals that replace the old Total seats pseudo-province rows.",
            "source": "Derived from data/raw/DPRD.csv and data/raw/DPRD2.csv.",
            "rows": output_counts["dprd_seat_totals.csv"],
            "columns": [
                "party_code",
                "party_name",
                "provincial_seats",
                "provincial_seats_total_row",
                "provincial_total_matches",
                "kabkot_seats",
                "kabkot_seats_total_row",
                "kabkot_total_matches",
                "kabkot_to_provincial_ratio",
                "ratio_defined",
            ],
        },
        {
            "filename": "dapil_seats.csv",
            "purpose": "Explicit DPR dapil seat counts externalized from the notebook into a CSV.",
            "source": f"{DAPIL_SEATS_SOURCE_LABEL}.",
            "rows": output_counts["dapil_seats.csv"],
            "columns": ["province", "district", "district_label", "seat_count", "source_file"],
        },
    ]

    notes = [
        "Province names are normalized to one canonical Indonesian title-case field while preserving the original source value in *_raw columns.",
        "The DPD source currently covers 37 provinces and does not include Papua Barat Daya.",
        "The DPRD2 source does not include DKI Jakarta, so kabkot seat counts for that province are absent by source.",
        "Undefined kabkot-to-provincial ratios are left blank and flagged with ratio_defined=false instead of using inf.",
        (
            "The DPRD provincial source has party-level mismatches between the province-row sums and the original Total seats row "
            f"for: {', '.join(provincial_total_mismatches)}. The prepared tables use the summed province rows as the authoritative values."
        ),
        "The current prepared DPR inputs still originate from data/processed/dpr_all.csv because the repo does not yet contain an equivalent raw structured DPR candidate file outside that table.",
    ]
    write_data_dictionary(metadata, notes)

    print("Prepared data written to", PREPARED_DIR)
    for filename, row_count in sorted(output_counts.items()):
        print(f" - {filename}: {row_count} rows")


if __name__ == "__main__":
    main()
