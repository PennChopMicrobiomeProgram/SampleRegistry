import collections
import csv
import os.path
import sqlite3
from datetime import datetime

from . import SQLALCHEMY_DATABASE_URI, engine, session
from .models import Base, Run, Sample, Annotation, StandardSampleType, StandardHostSpecies


def create_test_db():
    print(SQLALCHEMY_DATABASE_URI)
    Base.metadata.create_all(engine)

    run1 = Run(run_accession = 1, run_date=datetime.now(), machine_type="Illumina", machine_kit="MiSeq", lane=1, data_uri="run1", comment="Test run 1")
    run2 = Run(run_accession = 2, run_date=datetime.now(), machine_type="Illumina", machine_kit="MiSeq", lane=1, data_uri="run2", comment="Test run 2")
    session.bulk_save_objects([run1, run2])

    sample1 = Sample(sample_accession = 1, sample_name="Sample1", run_accession=run1.run_accession, barcode_sequence="AAAA", primer_sequence="TTTT", sample_type="Stool", subject_id="Subject1", host_species="Human")
    sample2 = Sample(sample_accession = 2, sample_name="Sample2", run_accession=run1.run_accession, barcode_sequence="CCCC", primer_sequence="GGGG", sample_type="Stool", subject_id="Subject2", host_species="Human")
    sample3 = Sample(sample_accession = 3, sample_name="Sample3", run_accession=run2.run_accession, barcode_sequence="GGGG", primer_sequence="CCCC", sample_type="Stool", subject_id="Subject3", host_species="Human")
    sample4 = Sample(sample_accession = 4, sample_name="Sample4", run_accession=run2.run_accession, barcode_sequence="TTTT", primer_sequence="AAAA", sample_type="Stool", subject_id="Subject4", host_species="Human")
    session.bulk_save_objects([sample1, sample2, sample3, sample4])

    session.add(Annotation(sample_accession=sample1.sample_accession, key="key1", val="val1"))
    session.add(Annotation(sample_accession=sample1.sample_accession, key="key2", val="val2"))
    session.add(Annotation(sample_accession=sample2.sample_accession, key="key1", val="val3"))
    session.add(Annotation(sample_accession=sample2.sample_accession, key="key2", val="val4"))
    session.add(Annotation(sample_accession=sample3.sample_accession, key="key1", val="val5"))
    session.add(Annotation(sample_accession=sample3.sample_accession, key="key2", val="val6"))
    session.add(Annotation(sample_accession=sample4.sample_accession, key="key1", val="val7"))
    session.add(Annotation(sample_accession=sample4.sample_accession, key="key2", val="val8"))

    try:
        init_standard_sample_types()
    except FileNotFoundError:
        session.add(StandardSampleType(sample_type="Stool", rarity="Uncommon", host_associated=True, comment="Poo"))
        session.add(StandardSampleType(sample_type="Blood", rarity="Common", host_associated=True, comment="Red stuff"))

    try:
        init_standard_host_species()
    except FileNotFoundError:
        session.add(StandardHostSpecies(host_species="Human", scientific_name="Person", ncbi_taxon_id=1))
        session.add(StandardHostSpecies(host_species="Mouse", scientific_name="FurryLittleDude", ncbi_taxon_id=2))

    session.commit()


def init_standard_sample_types():
    with open('standard_sample_types.tsv', 'r') as file:
        reader = csv.reader(file, delimiter='\t')
        next(reader)  # Skip header row
        sample_types = []
        for row in reader:
            sample_type = row[0]
            rarity = row[1]
            host_associated = bool(row[2])
            comment = row[3]
            sample_types.append(StandardSampleType(sample_type=sample_type, rarity=rarity, host_associated=host_associated, comment=comment))
        session.bulk_save_objects(sample_types)


def init_standard_host_species():
    with open('standard_host_species.tsv', 'r') as file:
        reader = csv.reader(file, delimiter='\t')
        next(reader)  # Skip header row
        host_species_list = []
        for row in reader:
            host_species = row[0]
            scientific_name = row[1]
            ncbi_taxon_id = row[2]
            host_species_list.append(StandardHostSpecies(host_species=host_species, scientific_name=scientific_name, ncbi_taxon_id=ncbi_taxon_id))
        session.bulk_save_objects(host_species_list)


class RegistryDatabase(object):
    def __init__(self, database_fp):
        self.db = database_fp
        self.con = sqlite3.connect(self.db)

    select_run_fp = "SELECT run_accession FROM runs WHERE data_uri = ?"
    
    select_run = (
        "SELECT data_uri FROM runs WHERE run_accession = ?"
        )

    select_sample_bc = (
        "SELECT sample_accession FROM samples WHERE "
        "run_accession = ? AND "
        "sample_name = ? AND "
        "barcode_sequence = ?"
        )

    select_samples = (
        "SELECT sample_accession FROM samples WHERE run_accession = ?"
    )

    select_sample_names_and_bc = (
        "SELECT sample_name, barcode_sequence FROM samples WHERE "
        "run_accession = ?"
    )

    delete_sample = (
        "DELETE FROM samples WHERE sample_accession = ?"
    )

    insert_run = (
        "INSERT INTO runs "
        "(run_date, machine_type, machine_kit, lane, data_uri, comment) "
        "VALUES (?, ?, ?, ?, ?, ?)"
        )

    insert_sample = (
        "INSERT INTO samples "
        "(run_accession, sample_name, barcode_sequence) "
        "VALUES (?, ?, ?)"
        )

    standard_annotation_keys = [
        "SampleType", "SubjectID", "HostSpecies"]
        
    select_standard_annotations = (
        "SELECT sample_type, subject_id, host_species "
        "FROM samples WHERE sample_accession = ?"
        )

    insert_standard_annotations = (
        "UPDATE samples "
        "SET sample_type = ?, subject_id = ?, host_species = ? "
        "WHERE sample_accession = ?"
        )

    delete_standard_annotations = (
        "UPDATE samples "
        "SET sample_type=NULL, subject_id=NULL, host_species=NULL "
        "WHERE sample_accession = ?"
        )

    select_nonstandard_annotations = (
        "SELECT `key`, `val` "
        "FROM annotations WHERE sample_accession = ?"
        )

    insert_nonstandard_annotation = (
        "INSERT INTO annotations "
        "(`sample_accession`, `key`, `val`) "
        "VALUES (?, ?, ?)"
        )

    delete_nonstandard_annotations = (
        "DELETE FROM annotations "
        "WHERE sample_accession = ?"
        )

    select_standard_sample_types = (
        "SELECT sample_type, host_associated, comment "
        "FROM standard_sample_types"
    )

    insert_standard_sample_type = (
        "INSERT INTO standard_sample_types "
        "(`sample_type`, `host_associated`, `comment`) "
        "VALUES (?, ?, ?)"
    )

    delete_standard_sample_types = (
        "DELETE FROM standard_sample_types "
        "WHERE 1"
    )

    select_standard_host_species = (
        "SELECT host_species, scientific_name, ncbi_taxon_id "
        "FROM standard_host_species"
    )

    insert_standard_host_species = (
        "INSERT INTO standard_host_species "
        "(`host_species`, `scientific_name`, `ncbi_taxon_id`) "
        "VALUES (?, ?, ?)"
    )

    delete_standard_host_species = (
        "DELETE FROM standard_host_species "
        "WHERE 1"
    )

    def query_standard_sample_types(self):
        cur = self.con.cursor()
        cur.execute(self.select_standard_sample_types)
        self.con.commit()
        res = cur.fetchall()
        cur.close()
        return res

    def register_standard_sample_types(self, sample_types):
        cur = self.con.cursor()
        cur.executemany(self.insert_standard_sample_type, sample_types)
        self.con.commit()
        cur.close()

    def remove_standard_sample_types(self):
        cur = self.con.cursor()
        cur.execute(self.delete_standard_sample_types)
        self.con.commit()
        cur.close()

    def query_standard_host_species(self):
        cur = self.con.cursor()
        cur.execute(self.select_standard_host_species)
        self.con.commit()
        res = cur.fetchall()
        cur.close()
        return res

    def register_standard_host_species(self, host_species):
        cur = self.con.cursor()
        cur.executemany(self.insert_standard_host_species, host_species)
        self.con.commit()
        cur.close()

    def remove_standard_host_species(self):
        cur = self.con.cursor()
        cur.execute(self.delete_standard_host_species)
        self.con.commit()
        cur.close()

    def create_tables(self):
        """Creates the necessary tables in a new database file.
        """
        this_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(this_dir))
        schema = open(os.path.join(base_dir, "schema.sql")).read()
        cur = self.con.cursor()
        cur.executescript(schema)
        self.con.commit()
        cur.close()

    def register_run(self, date, mach_type, mach_kit, lane, fp, comment):
        """Register a new sequencing run.

        Returns the accession number of the new run.
        """
        existing_run_acc = self._query_run_from_file(fp)
        if existing_run_acc:
            raise ValueError(
                "Run data already registered as %s" % existing_run_acc)
        cur = self.con.cursor()
        cur.execute(
            self.insert_run,
            (date, mach_type, mach_kit, lane, fp, comment))
        self.con.commit()
        accession = cur.lastrowid
        cur.close()
        return accession

    def _query_run_from_file(self, fp):
        cur = self.con.cursor()
        cur.execute(self.select_run_fp, (fp,))
        self.con.commit()
        res = cur.fetchone()
        cur.close()
        if res is not None:
            return res[0]
        else:
            return None

    def query_run_exists(self, run_accession):
        return self.query_run_file(run_accession) is not None

    def query_run_file(self, run_accession):
        cur = self.con.cursor()
        cur.execute(self.select_run, (run_accession,))
        self.con.commit()
        res = cur.fetchone()
        cur.close()
        if res is not None:
            return res[0]
        else:
            return None

    def register_samples(self, run_accession, sample_bcs):
        """Registers samples from tuples of SampleID, BarcodeSequence.

        Returns a list of sample accessions.
        """
        sample_tups = [(run_accession, n, b) for n, b in sample_bcs]
        for s in sample_tups:
            cur = self.con.cursor()
            cur.execute(self.select_sample_bc, s)
            self.con.commit()
            res = cur.fetchone()
            cur.close()
            if res is not None:
                raise ValueError("Sample already registered: {0}".format(s))
        accessions = []
        cur = self.con.cursor()
        for s in sample_tups:
            cur.execute(self.insert_sample, s)
            self.con.commit()
            accessions.append(cur.lastrowid)
        cur.close()
        return accessions

    def query_barcoded_sample_accessions(self, run_accession, sample_bcs):
        """Looks up sample accessions from tuples of name, bc.

        Returns a list of sample accessions.
        """
        sample_tups = [(run_accession, n, b) for n, b in sample_bcs]
        res = []
        for s in sample_tups:
            cur = self.con.cursor()
            cur.execute(self.select_sample_bc, s)
            self.con.commit()
            res.append(cur.fetchone())
            cur.close()
        return [r[0] if r else None for r in res]

    def query_sample_accessions(self, run_accession):
        """Find all sample accessions for a run."""
        cur = self.con.cursor()
        cur.execute(self.select_samples, (run_accession, ))
        self.con.commit()
        res = cur.fetchall()
        cur.close()
        return [r[0] for r in res]

    def query_sample_barcodes(self, run_accession):
        """Find sample names and barcodes for a run."""
        cur = self.con.cursor()
        cur.execute(self.select_sample_names_and_bc, (run_accession, ))
        self.con.commit()
        res = cur.fetchall()
        cur.close()
        return list(res)

    def remove_samples(self, sample_accessions):
        """Removes samples by accession number."""
        cur = self.con.cursor()
        sample_accession_vals = [(acc,) for acc in sample_accessions]
        cur.executemany(self.delete_sample, sample_accession_vals)
        self.con.commit()
        cur.close()

    def remove_annotations(self, sample_accessions):
        """Removes annotations from a sequence of sample accessions.
        """
        cur = self.con.cursor()
        sample_accession_vals = [(acc,) for acc in sample_accessions]
        cur.executemany(
            self.delete_standard_annotations, sample_accession_vals)
        cur.executemany(
            self.delete_nonstandard_annotations, sample_accession_vals)
        self.con.commit()
        cur.close()

    def query_sample_annotations(self, sample_accession):
        """Get annotations for a sample, given an accession number.

        Returns a dict of annotations.
        """
        annotations = {}
        annotations.update(
            self._query_standard_annotations(sample_accession))
        annotations.update(
            self._query_nonstandard_annotations(sample_accession))
        return annotations

    def _query_standard_annotations(self, sample_accession):
        cur = self.con.cursor()
        cur.execute(
            self.select_standard_annotations, (sample_accession,))
        self.con.commit()
        res = cur.fetchone()
        cur.close()
        pairs = zip(self.standard_annotation_keys, res)
        annotations = dict((k, v) for k, v in pairs if v is not None)
        return annotations

    def _query_nonstandard_annotations(self, sample_accession):
        cur = self.con.cursor()
        cur.execute(
            self.select_nonstandard_annotations, (sample_accession,))
        self.con.commit()
        res = cur.fetchall()
        cur.close()
        annotations = dict((k, v) for k, v in res if v is not None)
        return annotations

    def register_annotations(self, annotations):
        """Registers annotations (expects triple of accession, key, val).
        """
        standard, nonstandard = self._split_standard_annotations(annotations)
        self._register_standard_annotations(standard)
        self._register_nonstandard_annotations(nonstandard)

    @classmethod
    def _split_standard_annotations(cls, annotations):
        standard_annotations = []
        other_annotations = []
        standard_keys = set(cls.standard_annotation_keys)
        for acc, key, val in annotations:
            if key in standard_keys:
                standard_annotations.append((acc, key, val))
            else:
                other_annotations.append((acc, key, val))
        return standard_annotations, other_annotations

    def _register_standard_annotations(self, annotations):
        sample_vals = self._collect_standard_annotations(annotations)
        sample_updates = [
            vals + [acc] for acc, vals in sample_vals.items()]
        cur = self.con.cursor()
        cur.executemany(self.insert_standard_annotations, sample_updates)
        self.con.commit()
        cur.close()

    @classmethod
    def _collect_standard_annotations(cls, annotations):
        """Transform standard annotations from EAV format to row format.
        """
        keys_to_idx = dict(
            (b, a) for a, b in enumerate(cls.standard_annotation_keys))
        def make_empty_row():
            return [None for x in cls.standard_annotation_keys]
        # sample_accession => [val for each standardized column]
        annotation_rows = collections.defaultdict(make_empty_row)
        for acc, key, val in annotations:
            # Find the position of this column
            idx = keys_to_idx[key]
            # Get current values for each column
            vals = annotation_rows[acc]
            # Set the value at this position
            vals[idx] = val
            # Store back in main dict of samples
            annotation_rows[acc] = vals
        return annotation_rows

    def _register_nonstandard_annotations(self, annotations):
        cur = self.con.cursor()
        cur.executemany(self.insert_nonstandard_annotation, annotations)
        self.con.commit()
        cur.close()
