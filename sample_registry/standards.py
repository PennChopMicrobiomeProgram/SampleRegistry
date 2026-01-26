from __future__ import annotations

import csv
from dataclasses import dataclass
from importlib import resources
from typing import Iterable

DATA_PACKAGE = "sample_registry.data"


@dataclass(frozen=True)
class StandardSampleType:
    sample_type: str
    rarity: str
    host_associated: bool
    description: str


@dataclass(frozen=True)
class StandardHostSpecies:
    host_species: str
    scientific_name: str
    ncbi_taxon_id: int


@dataclass(frozen=True)
class MachineType:
    prefix: str
    machine_type: str


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


def _read_tsv_rows(filename: str, min_columns: int) -> list[list[str]]:
    data_path = resources.files(DATA_PACKAGE) / filename
    rows: list[list[str]] = []
    with resources.as_file(data_path) as path:
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.reader(handle, delimiter="\t")
            for row_index, row in enumerate(reader):
                if row_index == 0:
                    continue
                if not row:
                    continue
                if row[0].startswith("#"):
                    continue
                if len(row) < min_columns:
                    raise ValueError(
                        f"Expected at least {min_columns} columns in {filename}, got {len(row)}"
                    )
                rows.append(row)
    return rows


class StandardSampleTypes:
    def __init__(self, entries: Iterable[StandardSampleType]):
        self._entries = list(entries)
        self._by_sample_type = {entry.sample_type: entry for entry in self._entries}

    @classmethod
    def load(cls) -> "StandardSampleTypes":
        rows = _read_tsv_rows("standard_sample_types.tsv", 4)
        entries = [
            StandardSampleType(
                sample_type=row[0],
                rarity=row[1],
                host_associated=_parse_bool(row[2]),
                description=row[3],
            )
            for row in rows
        ]
        return cls(entries)

    def all(self) -> list[StandardSampleType]:
        return list(self._entries)

    def get(self, sample_type: str) -> StandardSampleType | None:
        return self._by_sample_type.get(sample_type)

    def names(self) -> list[str]:
        return list(self._by_sample_type.keys())

    def is_standard(self, sample_type: str) -> bool:
        return sample_type in self._by_sample_type


class StandardHostSpeciesList:
    def __init__(self, entries: Iterable[StandardHostSpecies]):
        self._entries = list(entries)
        self._by_host_species = {entry.host_species: entry for entry in self._entries}

    @classmethod
    def load(cls) -> "StandardHostSpeciesList":
        rows = _read_tsv_rows("standard_host_species.tsv", 3)
        entries = [
            StandardHostSpecies(
                host_species=row[0],
                scientific_name=row[1],
                ncbi_taxon_id=int(row[2]),
            )
            for row in rows
        ]
        return cls(entries)

    def all(self) -> list[StandardHostSpecies]:
        return list(self._entries)

    def get(self, host_species: str) -> StandardHostSpecies | None:
        return self._by_host_species.get(host_species)

    def names(self) -> list[str]:
        return list(self._by_host_species.keys())

    def is_standard(self, host_species: str) -> bool:
        return host_species in self._by_host_species


class MachineTypeMappings:
    def __init__(self, entries: Iterable[MachineType]):
        self._entries = list(entries)
        self._by_prefix = {entry.prefix: entry.machine_type for entry in self._entries}

    @classmethod
    def load(cls) -> "MachineTypeMappings":
        rows = _read_tsv_rows("machine_types.tsv", 2)
        entries = [MachineType(prefix=row[0], machine_type=row[1]) for row in rows]
        return cls(entries)

    def all(self) -> list[MachineType]:
        return list(self._entries)

    def get(self, prefix: str) -> str | None:
        return self._by_prefix.get(prefix)

    def prefixes(self) -> list[str]:
        return list(self._by_prefix.keys())

    def values(self) -> list[str]:
        return list(self._by_prefix.values())

    def as_dict(self) -> dict[str, str]:
        return dict(self._by_prefix)


STANDARD_SAMPLE_TYPES = StandardSampleTypes.load()
STANDARD_HOST_SPECIES = StandardHostSpeciesList.load()
MACHINE_TYPE_MAPPINGS = MachineTypeMappings.load()
