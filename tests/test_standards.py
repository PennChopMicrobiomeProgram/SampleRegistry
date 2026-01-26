from sample_registry.standards import (
    MACHINE_TYPE_MAPPINGS,
    STANDARD_HOST_SPECIES,
    STANDARD_SAMPLE_TYPES,
)


def test_standard_sample_types_loaded():
    feces = STANDARD_SAMPLE_TYPES.get("Feces")
    assert feces is not None
    assert feces.host_associated is True
    assert "fecal" in feces.description.lower()


def test_standard_host_species_loaded():
    human = STANDARD_HOST_SPECIES.get("Human")
    assert human is not None
    assert human.scientific_name == "Homo sapiens"
    assert human.ncbi_taxon_id == 9606


def test_machine_type_mappings_loaded():
    assert MACHINE_TYPE_MAPPINGS.get("VH") == "Illumina-NextSeq"
    assert MACHINE_TYPE_MAPPINGS.get("SH") == "Illumina-MiSeq"
    assert "Illumina-NovaSeq" in MACHINE_TYPE_MAPPINGS.values()
