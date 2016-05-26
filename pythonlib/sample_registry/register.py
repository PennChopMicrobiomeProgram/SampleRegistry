"""Add samples and runs to the registry"""

import argparse
import itertools
import os
import re
import sys
import gzip

from sample_registry.db import CoreDb
from sample_registry.mapping import SampleTable


__THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_DATABASE = CoreDb(__THIS_DIR + "/../../website/core.db")


SAMPLES_DESC = """\
Add new samples to the registry, with annotations.
"""

ANNOTATIONS_DESC = """\
Replace annotations for samples in the registry.  Samples are matched
using the sample ID and barcode sequence.
"""

ANNOTATIONS_EPILOG = """\
**BEWARE USER** This script will replace all existing annotations with
those found in the provided file!  Make sure this is what you want, or
you will be restoring database tables from backup files, as you deserve.
You have been warned!!!
"""

SAMPLE_TABLE_HELP = """\
Sample table in tab-separated values (TSV) format.  Field names are
listed in the first line.  If the first line begins with '#', the
character is ignored.  Other lines beginning with '#' are interpreted
as comments.
"""

def unregister_samples(argv=None, coredb=REGISTRY_DATABASE, out=sys.stdout):
    p = argparse.ArgumentParser(
        description="Remove samples for a sequencing run from the registry.")
    p.add_argument("run_accession", type=int, help="Run accession number")
    args = p.parse_args(argv)

    registry = SampleRegistry(coredb)
    registry.check_run_accession(args.run_accession)
    samples_removed = registry.remove_samples(args.run_accession)
    out.write("Removed {0} samples: {1}".format(
        len(samples_removed), samples_removed))


def register_samples():
    return register_sample_annotations(None, True)


def register_annotations():
    return register_sample_annotations(None, False)


def register_sample_annotations(
        argv=None, register_samples=False, coredb=REGISTRY_DATABASE,
        out=sys.stdout):

    if register_samples:
        p = argparse.ArgumentParser(description=SAMPLES_DESC)
    else:
        p = argparse.ArgumentParser(
            description=ANNOTATIONS_DESC, epilog=ANNOTATIONS_EPILOG)

    p.add_argument(
        "run_accession", type=int,
        help="Run accession number")
    p.add_argument(
        "sample_table", type=argparse.FileType('r'),
        help=SAMPLE_TABLE_HELP)
    args = p.parse_args(argv)

    registry = SampleRegistry(coredb)
    sample_table = SampleTable.load(args.sample_table)
    sample_table.look_up_nextera_barcodes()
    sample_table.validate()

    registry.check_run_accession(args.run_accession)
    if register_samples:
        registry.register_samples(args.run_accession, sample_table)
    registry.register_annotations(args.run_accession, sample_table)

def parse_illumina_fastq_header(line):
    if not line.startswith("@"):
        raise RuntimeError("Not a FASTQ header line")
    # Remove first character, @
    line = line[1:]
    word1, _, word2 = line.partition(" ")

    keys1 = [
        "instrument", "run_number", "flowcell_id", "lane",
        "tile", "xpos", "ypos",
        ]
    vals1 = dict((k, v) for k, v in zip(keys1, word1.split(":")))

    keys2 = [
        "read", "is_filtered", "control_number", "index_reads",
        ]
    vals2 = dict((k, v) for k, v in zip(keys2, word2.split(":")))

    vals1.update(vals2)
    return vals1


# From https://www.safaribooksonline.com/library/view/python-cookbook/0596001673/ch04s16.html
def splitall(path):
    allparts = []
    while 1:
        left, right = os.path.split(path)
        if left == path:  # sentinel for absolute paths
            allparts.insert(0, left)
            break
        elif right == path: # sentinel for relative paths
            allparts.insert(0, right)
            break
        else:
            path = left
            allparts.insert(0, right)
    return allparts


def parse_illumina_folder_date(dirname):
    dirs = splitall(dirname)
    rundir = dirs[1]
    if re.match("\\d{6}_", rundir):
        year = rundir[0:2]
        month = rundir[2:4]
        day = rundir[4:6]
        return "20{0}-{1}-{2}".format(year, month, day)
    return None


def register_illumina_file(argv=None, coredb=REGISTRY_DATABASE, out=sys.stdout):
    p = argparse.ArgumentParser(
        description="Add a new run to the registry from an Illumina FASTQ file")
    p.add_argument("filepath", type=argparse.FileType("r"))
    p.add_argument("--date", help="Run date (YYYY-MM-DD)")
    p.add_argument("--comment", required=True, help="Comment (free text)")
    args = p.parse_args(argv)

    if args.filepath.name.endswith(".gz"):
        fastq_file = gzip.GzipFile(fileobj=args.filepath)
    else:
        fastq_file = args.filepath
    first_line = next(fastq_file).strip()
    fastq_info = parse_illumina_fastq_header(first_line)

    if args.date is not None:
        date = args.date
    else:
        date = parse_illumina_folder_date(args.filepath.name)
    if date is None:
        p.error("Could not find date in folder name, and no --date supplied")

    if fastq_info["instrument"].startswith("D"):
        run_type = "Illumina-HiSeq"
    else:
        run_type = "Illumina-MiSeq"
    lane = fastq_info["lane"]
    fastq_filepath = args.filepath.name

    acc = coredb.register_run(
        date, run_type, "Nextera XT", lane, fastq_filepath, args.comment)
    out.write(u"Registered run %s in the database\n" % acc)


def register_run(argv=None, coredb=REGISTRY_DATABASE, out=sys.stdout):
    machines = [
        "Illumina-MiSeq",
        "Illumina-HiSeq",
    ]
    kits = [
        "Nextera XT"
    ]

    p = argparse.ArgumentParser(
        description="Add a new run to the registry")
    # Should be positional argument. Read additional info straight
    # from the file.  Maybe support a manual override, or just edit
    # the database directly.
    p.add_argument(
        "--file", required=True,
        help="Resource filepath (not checked for validity)")
    # Remove and read from file
    p.add_argument(
        "--date", required=True,
        help="Run date (YYYY-MM-DD)")
    # Keep this
    p.add_argument(
        "--comment", required=True,
        help="Comment (free text)")
    # Remove and read from file
    p.add_argument(
        "--type", default="Immulina-MiSeq", choices=machines,
        help="Machine type")
    # Keep this?
    p.add_argument(
        "--kit", default="Nextera XT", choices=kits,
        help="Machine kit")
    # Remove and read from file
    p.add_argument("--lane", default="1",
        help="Lane number")
    args = p.parse_args(argv)

    acc = coredb.register_run(
        args.date, args.type, args.kit, args.lane, args.file, args.comment)
    out.write(u"Registered run %s in the database\n" % acc)


def get_illumina_info(f):
    """Read Illumina run info from a FASTQ file."""
    # Structure of header line:
    # @<instrument>:<run number>:<flowcell ID>:<lane>:<tile>:<x-pos>:<y-pos>
    # <read>:<is filtered>:<control number>:<sample number>
    header_line = next(f)
    if not header_line.startswith("@"):
        raise ValueError("Expected FASTQ header line, saw %s" % header_line)
    # Remove '@' from beginning of line
    header_line = header_line[1:].rstrip()
    run_delim, read_delim = header_line.split(" ")
    run_keys = ("instrument", "run_number", "flowcell_id", "lane")
    info = _collect_delimited_vals(run_delim, run_keys)
    read_keys = ("read", "is_filtered", "control_num", "barcode_seq")
    info.update(_collect_delimited_vals(read_delim, read_keys))
    return info

def _collect_delimited_vals(text, keys, sep=":"):
    vals = text.split(sep)
    return dict(zip(keys, vals))

class SampleRegistry(object):
    def __init__(self, registry_db):
        self.db = registry_db

    def check_run_accession(self, acc):
        if not self.db.query_run_exists(acc):
            raise ValueError("Run does not exist %s" % acc)

    def register_samples(self, run_accession, sample_table):
        self.db.register_samples(run_accession, sample_table.core_info)

    def remove_samples(self, run_accession):
        accessions = self.db.query_sample_accessions(run_accession)
        self.db.remove_annotations(accessions)
        self.db.remove_samples(accessions)
        return accessions

    def register_annotations(self, run_accession, sample_table):
        accessions = self._get_sample_accessions(run_accession, sample_table)
        annotation_args = []
        for a, pairs in zip(accessions, sample_table.annotations):
            for k, v in pairs:
                annotation_args.append((a, k, v))
        self.db.remove_annotations(accessions)
        self.db.register_annotations(annotation_args)

    def _get_sample_accessions(self, run_accession, sample_table):
        args = [(run_accession, n, b) for n, b in sample_table.core_info]
        accessions = self.db.query_barcoded_sample_accessions(
            run_accession, sample_table.core_info
        )
        unaccessioned_recs = []
        for accession, rec in zip(accessions, sample_table.recs):
            if accession is None:
                unaccessioned_recs.append(rec)
        if unaccessioned_recs:
            raise IOError("Not accessioned: %s" % unaccessioned_recs)
        return accessions
