"""Add samples and runs to the registry"""

import argparse
import sys
import gzip
from sqlalchemy.orm import Session
from typing import Generator
from sample_registry.mapping import SampleTable
from sample_registry.registrar import SampleRegistry
from seqBackupLib.illumina import IlluminaFastq


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


def unregister_samples(argv=None, session: Session = None, out=sys.stdout):
    p = argparse.ArgumentParser(
        description="Remove samples for a sequencing run from the registry."
    )
    p.add_argument("run_accession", type=int, help="Run accession number")
    args = p.parse_args(argv)

    registry = SampleRegistry(session)
    registry.check_run_accession(args.run_accession)
    samples_removed = registry.remove_samples(args.run_accession)

    registry.session.commit()
    out.write("Removed {0} samples: {1}".format(len(samples_removed), samples_removed))


def register_samples():

    return register_sample_annotations(None, True)


def register_annotations():
    return register_sample_annotations(None, False)


def register_sample_annotations(
    argv=None, register_samples=False, session: Session = None
):
    if register_samples:
        p = argparse.ArgumentParser(description=SAMPLES_DESC)
    else:
        p = argparse.ArgumentParser(
            description=ANNOTATIONS_DESC, epilog=ANNOTATIONS_EPILOG
        )
    p.add_argument("run_accession", type=int, help="Run accession number")
    p.add_argument("sample_table", type=argparse.FileType("r"), help=SAMPLE_TABLE_HELP)
    args = p.parse_args(argv)

    registry = SampleRegistry(session)

    if register_samples:
        registry.check_samples(args.run_accession, exists=False)

    sample_table = SampleTable.load(args.sample_table)
    sample_table.look_up_nextera_barcodes()
    sample_table.validate()

    registry.check_run_accession(args.run_accession)
    if register_samples:
        registry.register_samples(args.run_accession, sample_table)
    registry.register_annotations(args.run_accession, sample_table)

    registry.session.commit()


def parse_tsv_ncol(f, ncol: int) -> Generator[tuple[str], None, None]:
    assert ncol > 0
    # Skip header
    next(f)
    for line in f:
        line = line.rstrip("\n")
        if line.startswith("#"):
            continue
        if not line.strip():
            continue
        vals = line.split("\t")
        if len(vals) < ncol:
            raise ValueError("Each line must contain at least {0} fields".format(ncol))
        yield tuple(vals[:ncol])


def register_sample_types(argv=None, session: Session = None):
    p = argparse.ArgumentParser(
        description=("Update the list of standard sample types in the registry")
    )
    p.add_argument("file", type=argparse.FileType("r"))
    args = p.parse_args(argv)

    registry = SampleRegistry(session)
    sample_types = list(parse_tsv_ncol(args.file, 4))
    registry.remove_standard_sample_types()
    registry.register_standard_sample_types(sample_types)

    registry.session.commit()


def register_host_species(argv=None, session: Session = None):
    p = argparse.ArgumentParser(
        description=("Update the list of standard host species in the registry")
    )
    p.add_argument("file", type=argparse.FileType("r"))
    args = p.parse_args(argv)

    registry = SampleRegistry(session)
    host_species = list(parse_tsv_ncol(args.file, 3))
    registry.remove_standard_host_species()
    registry.register_standard_host_species(host_species)

    registry.session.commit()


def register_illumina_file(argv=None, session: Session = None, out=sys.stdout):
    p = argparse.ArgumentParser(
        description=("Add a new run to the registry from a gzipped Illumina FASTQ file")
    )
    p.add_argument("file")
    p.add_argument("comment", help="Comment (free text)")
    args = p.parse_args(argv)

    registry = SampleRegistry(session)
    f = IlluminaFastq(gzip.open(args.file, "rt"))
    acc = registry.register_run(
        f.folder_info["date"],
        f.machine_type,
        "Nextera XT",
        f.lane,
        str(f.filepath),
        args.comment,
    )

    registry.session.commit()
    out.write("Registered run {0} in the database\n".format(acc))


def register_run(argv=None, session: Session = None, out=sys.stdout):
    p = argparse.ArgumentParser(description="Add a new run to the registry")
    p.add_argument("file", help="Resource filepath (not checked)")
    p.add_argument("--date", required=True, help="Run date (YYYY-MM-DD)")
    p.add_argument("--comment", required=True, help="Comment (free text)")
    p.add_argument(
        "--type",
        default="Illumina-MiSeq",
        choices=SampleRegistry.machines,
        help="Machine type",
    )
    p.add_argument("--lane", default="1", help="Lane number")
    args = p.parse_args(argv)

    registry = SampleRegistry(session)
    acc = registry.register_run(
        args.date, args.type, "Nextera XT", args.lane, args.file, args.comment
    )

    registry.session.commit()
    out.write("Registered run %s in the database\n" % acc)


def modify_run(argv=None, session: Session = None):
    p = argparse.ArgumentParser(description="Modify an existing run in the registry")
    p.add_argument("run_accession", type=int, help="Run accession number")
    p.add_argument("--date", help="Run date (YYYY-MM-DD)")
    p.add_argument("--comment", help="Comment (free text)")
    p.add_argument(
        "--type",
        choices=SampleRegistry.machines,
        help="Machine type",
    )
    p.add_argument("--kit", help="Machine kit")
    p.add_argument("--lane", type=int, help="Lane number")
    p.add_argument("--data_uri", help="Data URI")
    p.add_argument("--admin_comment", help="Admin comment")
    args = p.parse_args(argv)

    registry = SampleRegistry(session)
    registry.check_run_accession(args.run_accession)
    registry.modify_run(
        run_accession=args.run_accession,
        run_date=args.date,
        machine_type=args.type,
        machine_kit=args.kit,
        lane=args.lane,
        data_uri=args.data_uri,
        comment=args.comment,
        admin_comment=args.admin_comment,
    )

    registry.session.commit()


def modify_sample(argv=None, session: Session = None):
    p = argparse.ArgumentParser(description="Modify an existing sample in the registry")
    p.add_argument("sample_accession", type=int, help="Sample accession number")
    p.add_argument("--sample_name", help="Sample name")
    p.add_argument("--sample_type", help="Sample type")
    p.add_argument("--subject_id", help="Subject ID")
    p.add_argument("--host_species", help="Host species")
    p.add_argument("--barcode_sequence", help="Barcode sequence")
    p.add_argument("--primer_sequence", help="Primer sequence")
    args = p.parse_args(argv)

    registry = SampleRegistry(session)
    registry.check_sample_accession(args.sample_accession)
    registry.modify_sample(
        sample_accession=args.sample_accession,
        sample_name=args.sample_name,
        sample_type=args.sample_type,
        subject_id=args.subject_id,
        host_species=args.host_species,
        barcode_sequence=args.barcode_sequence,
        primer_sequence=args.primer_sequence,
    )

    registry.session.commit()


def modify_annotation(argv=None, session: Session = None):
    p = argparse.ArgumentParser(
        description="Modify an existing annotation in the registry"
    )
    p.add_argument("sample_accession", type=int, help="Sample accession number")
    p.add_argument("key", help="Annotation key")
    p.add_argument("val", help="Annotation value")
    args = p.parse_args(argv)

    registry = SampleRegistry(session)
    registry.check_sample_accession(args.sample_accession)
    registry.modify_annotation(
        sample_accession=args.sample_accession, key=args.key, val=args.val
    )

    registry.session.commit()
