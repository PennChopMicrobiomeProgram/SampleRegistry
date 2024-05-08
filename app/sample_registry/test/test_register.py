import gzip
import io
import os
import shutil
import tempfile
import unittest

from sample_registry.db import RegistryDatabase
from sample_registry.mapping import SampleTable
from sample_registry.register import (
    register_run, register_sample_annotations,
    unregister_samples, register_illumina_file,
    register_sample_types,
    register_host_species,
)


def temp_sample_file(samples):
    f = tempfile.NamedTemporaryFile(mode="wt")
    t = SampleTable(samples)
    t.write(f)
    f.seek(0)
    return f


class RegisterScriptTests(unittest.TestCase):
    def setUp(self):
        self.db = RegistryDatabase(":memory:")
        self.db.create_tables()
        self.run_args = [
            "abc",
            "--lane", "1",
            "--date", "2008-09-21",
            "--type", "Illumina-MiSeq",
            "--comment", "mdsnfa adsf",
        ]
        self.samples = [{
            "SampleID": "abc123",
            "BarcodeSequence": "GGGCCT",
            "SampleType": "Oral swab",
            "bb": "cd e29",
        }]

    def test_register_run(self):
        out = io.StringIO()
        register_run(self.run_args, self.db, out)

        # Check that accession number is printed
        self.assertEqual(
            out.getvalue(),
            "Registered run 1 in the database\n"
        )

        # Check that attributes are saved in the database
        self.assertEqual(self.db.query_run_file(1), "abc")

    def test_register_illumina_file(self):
        tmp_dir = tempfile.mkdtemp()
        fastq_dir = (
            "Miseq/160511_M03543_0047_000000000-APE6Y/Data/Intensities/"
            "BaseCalls")
        fastq_name = "Undetermined_S0_L001_R1_001.fastq.gz"

        os.makedirs(os.path.join(tmp_dir, fastq_dir))
        relative_fp = os.path.join(fastq_dir, fastq_name)
        absolute_fp = os.path.join(tmp_dir, relative_fp)
        f = gzip.open(absolute_fp, "wt")
        f.write("@M03543:21:C8LJ2ANXX:1:2209:1084:2044 1:N:0:NNNNNNNN+NNNNNNNN")
        f.close()

        out = io.StringIO()
        original_cwd = os.getcwd()
        os.chdir(tmp_dir)
        try:
            register_illumina_file(
                [relative_fp, "abcd efg"], self.db, out)
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(tmp_dir)

        self.assertEqual(self.db.query_run_file(1), relative_fp)

    def test_register_samples(self):
        register_run(self.run_args, self.db)
        out = io.StringIO()
        sample_file = temp_sample_file(self.samples)
        args = ["1", sample_file.name]
        register_sample_annotations(args, True, self.db, out)

        # Check that accession number is assigned
        obs_accessions = self.db.query_barcoded_sample_accessions(
            1, [("abc123", "GGGCCT")])
        self.assertEqual(obs_accessions, [1])

        # Check that annotations are saved to the database
        self.assertEqual(
            self.db.query_sample_annotations(1),
            {"SampleType": "Oral swab", "bb": "cd e29"})

    def test_register_annotations(self):
        register_run(self.run_args, self.db)
        sample_file = temp_sample_file(self.samples)
        args = [ "1", sample_file.name]
        register_sample_annotations(args, True, self.db)

        # Update SampleType, add fg
        new_annotations = {"SampleType": "Feces", "fg": "hi5 34"}
        modified_samples = [x.copy() for x in self.samples]
        modified_samples[0].update(new_annotations)
        # Remove bb
        del modified_samples[0]["bb"]
        sample_file = temp_sample_file(modified_samples)
        args = ["1", sample_file.name]
        register_sample_annotations(args, False, self.db)

        self.assertEqual(
            self.db.query_sample_annotations(1), new_annotations)

    def test_unregister_samples(self):
        register_run(self.run_args, self.db)
        out = io.StringIO()
        sample_file = temp_sample_file(self.samples)
        args = ["1", sample_file.name]
        register_sample_annotations(args, True, self.db, out)

        unregister_samples(["1"], self.db)
        self.assertEqual(self.db._query_nonstandard_annotations(1), {})
        self.assertEqual(self.db.query_sample_accessions(1), [])

    def test_register_sample_types(self):
        f = tempfile.NamedTemporaryFile("wt")
        f.write(SAMPLE_TYPES_TSV)
        f.seek(0)

        register_sample_types([f.name], self.db)
        self.assertEqual(
            self.db.query_standard_sample_types(),
            SAMPLE_TYPES_VALS)

        # Add a new sample type and re-register
        new_line = "Extra type	1	Just to test"
        f2 = tempfile.NamedTemporaryFile("wt")
        f2.write(SAMPLE_TYPES_TSV + new_line)
        f2.seek(0)

        register_sample_types([f2.name], self.db)
        self.assertEqual(
            self.db.query_standard_sample_types(),
            SAMPLE_TYPES_VALS + [("Extra type", 1, "Just to test")])

    def test_register_host_species(self):
        f = tempfile.NamedTemporaryFile("wt")
        f.write(HOST_SPECIES_TSV)
        f.seek(0)

        register_host_species([f.name], self.db)
        self.assertEqual(
            self.db.query_standard_host_species(),
            HOST_SPECIES_VALS)

        # Add a new species to the file and re-register
        new_line = "Hippo	Test	1243"
        f2 = tempfile.NamedTemporaryFile("wt")
        f2.write(HOST_SPECIES_TSV + new_line)
        f2.seek(0)

        register_host_species([f2.name], self.db)
        self.assertEqual(
            self.db.query_standard_host_species(),
            HOST_SPECIES_VALS + [("Hippo", "Test", 1243)])


SAMPLE_TYPES_TSV = """\
sample_type	host_associated	description

# Gut
Feces	1	Human and animal fecal material.
Rectal swab	1	Results are sensitive to collection method.
Ostomy fluid	1	
Colonic biopsy	1	

# Oral
Oral wash	1	
"""

SAMPLE_TYPES_VALS = [
    ("Feces", 1, "Human and animal fecal material."),
    ("Rectal swab", 1, "Results are sensitive to collection method."),
    ("Ostomy fluid", 1, ""),
    ("Colonic biopsy", 1, ""),
    ("Oral wash", 1, ""),
]

HOST_SPECIES_TSV = """\
host_species	scientific_name	ncbi_taxid
Human	Homo sapiens	9606
Mouse	Mus musculus	10090
"""

HOST_SPECIES_VALS = [
    ("Human", "Homo sapiens", 9606),
    ("Mouse", "Mus musculus", 10090),
]
