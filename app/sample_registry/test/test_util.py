import collections
import io
import unittest

from sample_registry.util import (
    key_by_attr, dict_from_eav, local_filepath,
    parse_fasta, parse_fastq, deambiguate, reverse_complement,
    )

class UtilTests(unittest.TestCase):
    def test_key_by_attr(self):
        A = collections.namedtuple("A", ["b", "c", "d"])
        a1 = A(b="1", c="2", d="3")
        a2 = A(b="4", c="5", d="6")
        a3 = A(b="1", c="8", d="9")
        xs = [a1, a2, a3]
        
        bs = key_by_attr(xs, "b")
        self.assertEqual(set(bs["1"]), set([a1, a3]))

    def test_dict_from_eav(self):
        xs = [
            ("a", "attr1", "bldj"),
            ("b", "attr1", "meh"),
            ("c", "attr1", "hey"),
            ("a", "mdk", "www")]
        self.assertEqual(dict_from_eav(xs, "a"), dict(attr1="bldj", mdk="www"))

    def test_local_filepath(self):
        # Normal filepath if no mountpoints given
        self.assertEqual(
            local_filepath("abc", None, None), "abc")
        # Absolute filepaths are ok
        self.assertEqual(
            local_filepath("/abc", None, None), "/abc")
        # Allow for local mount point
        self.assertEqual(
            local_filepath("/abc", "/mnt/files", None), "/mnt/files/abc")
        # Allow for non-root folder of remote host to be mounted locally
        self.assertEqual(
            local_filepath("/abc/def", "/mnt/files", "/abc"), "/mnt/files/def")
        # Remote mount point not used if no local mount point is given
        self.assertEqual(
            local_filepath("/abc/def", None, "/jhsdf"), "/abc/def")

    def test_parse_fasta(self):
        obs = parse_fasta(io.StringIO(fasta1))
        self.assertEqual(next(obs), ("seq1 hello", "ACGTGGGTTAA"))
        self.assertEqual(next(obs), ("seq 2", "GTTCCGAAA"))
        self.assertEqual(next(obs), ("seq3", ""))
        self.assertRaises(StopIteration, next, obs)

    def test_parse_fastq(self):
        obs = parse_fastq(io.StringIO(fastq1))
        self.assertEqual(next(obs), (
            "YesYes", "AGGGCCTTGGTGGTTAG", ";234690GSDF092384"))
        self.assertEqual(next(obs), (
            "Seq2:with spaces", "GCTNNNNNNNNNNNNNNN", "##################"))
        self.assertRaises(StopIteration, next, obs)

    def test_deambiguate(self):
        obs = set(deambiguate("AYGR"))
        exp = set(["ACGA", "ACGG", "ATGA", "ATGG"])
        self.assertEqual(obs, exp)

        obs = set(deambiguate("AGN"))
        exp = set(["AGA", "AGC", "AGG", "AGT"])
        self.assertEqual(obs, exp)

    def test_reverse_complement(self):
        self.assertEqual(reverse_complement("AGATC"), "GATCT")
        self.assertRaises(KeyError, reverse_complement, "ANCC")


fasta1 = u"""\
>seq1 hello
ACGTGG
GTTAA
>seq 2
GTTC
C
GAAA
>seq3
"""

fastq1 = u"""\
@YesYes
AGGGCCTTGGTGGTTAG
+
;234690GSDF092384
@Seq2:with spaces
GCTNNNNNNNNNNNNNNN
+
##################
"""

if __name__ == '__main__':
    unittest.main()
