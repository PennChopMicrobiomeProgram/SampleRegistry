import collections
import io
from sample_registry.util import (
    key_by_attr,
    dict_from_eav,
    local_filepath,
    parse_fasta,
    parse_fastq,
    deambiguate,
    reverse_complement,
)


def test_key_by_attr():
    A = collections.namedtuple("A", ["b", "c", "d"])
    a1 = A(b="1", c="2", d="3")
    a2 = A(b="4", c="5", d="6")
    a3 = A(b="1", c="8", d="9")
    xs = [a1, a2, a3]

    bs = key_by_attr(xs, "b")
    assert set(bs["1"]) == set([a1, a3])


def test_dict_from_eav():
    xs = [
        ("a", "attr1", "bldj"),
        ("b", "attr1", "meh"),
        ("c", "attr1", "hey"),
        ("a", "mdk", "www"),
    ]
    assert dict_from_eav(xs, "a") == dict(attr1="bldj", mdk="www")


def test_local_filepath():
    # Normal filepath if no mountpoints given
    assert local_filepath("abc", None, None) == "abc"
    # Absolute filepaths are ok
    assert local_filepath("/abc", None, None) == "/abc"
    # Allow for local mount point
    assert local_filepath("/abc", "/mnt/files", None) == "/mnt/files/abc"
    # Allow for non-root folder of remote host to be mounted locally
    assert local_filepath("/abc/def", "/mnt/files", "/abc") == "/mnt/files/def"
    # Remote mount point not used if no local mount point is given
    assert local_filepath("/abc/def", None, "/jhsdf") == "/abc/def"


def test_parse_fasta():
    obs = parse_fasta(io.StringIO(fasta1))
    assert next(obs) == ("seq1 hello", "ACGTGGGTTAA")
    assert next(obs) == ("seq 2", "GTTCCGAAA")
    assert next(obs) == ("seq3", "")
    try:
        next(obs)
        assert False, "Expected StopIteration"
    except StopIteration:
        pass


def test_parse_fastq():
    obs = parse_fastq(io.StringIO(fastq1))
    assert next(obs) == ("YesYes", "AGGGCCTTGGTGGTTAG", ";234690GSDF092384")
    assert next(obs) == ("Seq2:with spaces", "GCTNNNNNNNNNNNNNNN", "##################")
    try:
        next(obs)
        assert False, "Expected StopIteration"
    except StopIteration:
        pass


def test_deambiguate():
    obs = set(deambiguate("AYGR"))
    exp = set(["ACGA", "ACGG", "ATGA", "ATGG"])
    assert obs == exp

    obs = set(deambiguate("AGN"))
    exp = set(["AGA", "AGC", "AGG", "AGT"])
    assert obs == exp


def test_reverse_complement():
    assert reverse_complement("AGATC") == "GATCT"
    try:
        reverse_complement("ANCC")
        assert False, "Expected KeyError"
    except KeyError:
        pass


fasta1 = """\
>seq1 hello
ACGTGG
GTTAA
>seq 2
GTTC
C
GAAA
>seq3
"""

fastq1 = """\
@YesYes
AGGGCCTTGGTGGTTAG
+
;234690GSDF092384
@Seq2:with spaces
GCTNNNNNNNNNNNNNNN
+
##################
"""
