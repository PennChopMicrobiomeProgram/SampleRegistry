"""Read, validate, and write sample info tables"""

import string


class SampleTable(object):
    # Arguably the core fields should be in a different class, because
    # they really are of concern to the database and not the table of
    # samples.
    CORE_FIELDS = ["SampleID", "BarcodeSequence"]

    NAs = set([
        "", "0000-00-00", "null", "Null", "NA", "na", "none", "None",
    ])

    def __init__(self, recs):
        self.recs = recs
        self._remove("Description")

    def _remove(self, field):
        for r in self.recs:
            if field in r:
                del r[field]

    @property
    def core_info(self):
        for r in self.recs:
            yield tuple(r.get(f, "") for f in self.CORE_FIELDS)

    @property
    def annotations(self):
        for r in self.recs:
            annotation_keys = set(r.keys()) - set(self.CORE_FIELDS)
            yield [(k, r[k]) for k in annotation_keys]

    def validate(self):
        _validate_sample_ids(self.recs)
        _validate_barcodes(self.recs)

    def write(self, f):
        rows = _cast(self.recs, self.CORE_FIELDS, [])
        for row in rows:
            f.write(u"\t".join(row))
            f.write(u"\n")

    @classmethod
    def load(cls, f):
        recs = list(cls._parse(f))
        if not recs:
            raise ValueError(
                "No records found in sample info file. "
                "Problem with windows line endings?")
        return cls(recs)

    @classmethod
    def _parse(cls, f):
        """Parse mapping file, return each record as a dict."""
        header = next(f).lstrip("#")
        keys = cls._tokenize(header)
        assert(all(keys)) # No blank fields in header
        for line in f:
            if line.startswith("#"):
                continue
            if not line.strip():
                continue
            vals = cls._tokenize(line)
            yield dict([(k, v) for k, v in zip(keys, vals) if v not in cls.NAs])

    @classmethod
    def _tokenize(cls, line):
        """Tokenize a single line"""
        line = line.rstrip("\n\r")
        toks = line.split("\t")
        return [t.strip() for t in toks]

    def look_up_nextera_barcodes(self):
        barcodes = dict(x.split() for x in NEXTERA_BARCODES.splitlines())
        for r in self.recs:
            if "BarcodeSequence" in r:
                continue
            try:
                fwd_index = r["barcode_index_fwd"]
                fwd_barcode = barcodes[fwd_index]
                rev_index = r["barcode_index_rev"]
                rev_barcode = barcodes[rev_index]
                r["BarcodeSequence"] = fwd_barcode + "-" + rev_barcode
            except KeyError as e:
                raise KeyError(
                    "Could not find DNA barcode sequence for this record:\n"
                    "%s\n%s" % (r, e)
                )


def _cast(records, left_cols, right_cols, missing="NA"):
    records = list(records)
    # Make a copy for appending
    left_cols = list(left_cols)
    all_cols = set(left_cols + right_cols)
    for r in records:
        for key in sorted(r.keys()):
            if key not in all_cols:
                left_cols.append(key)
                all_cols.add(key)

    header = left_cols + right_cols
    yield header

    for r in records:
        row = [missing for _ in header]
        for key, val in r.items():
            idx = header.index(key)
            row[idx] = val
        yield row


def _validate_sample_ids(recs):
    seen = set()
    allowed = set("." + string.ascii_letters + string.digits)
    allowed_start = set(string.ascii_letters)
    for r in recs:
        sample_id = r["SampleID"]
        if sample_id in seen:
            raise ValueError("Duplicated sample ID: %s" % r)
        seen.add(sample_id)
        if not all(char in allowed for char in sample_id):
            raise ValueError("Illegal characters in sample ID: %s" % r)
        if not sample_id[0] in allowed_start:
            raise ValueError("Sample ID must begin with a letter: %s" % r)


def _validate_barcodes(recs):
    seen = set()
    allowed = set("AGCT-")
    for r in recs:
        barcode = r["BarcodeSequence"]
        if barcode in seen:
            raise ValueError("Duplicated barcode: %s" % r)
        seen.add(barcode)
        if not all(char in allowed for char in barcode):
            raise ValueError("Illegal characters in barcode: %s" % r)


NEXTERA_BARCODES = u"""\
N701	TAAGGCGA
N702	CGTACTAG
N703	AGGCAGAA
N704	TCCTGAGC
N705	GGACTCCT
N706	TAGGCATG
N707	CTCTCTAC
N708	CAGAGAGG
N709	GCTACGCT
N710	CGAGGCTG
N711	AAGAGGCA
N712	GTAGAGGA
N714	GCTCATGA
N715	ATCTCAGG
N716	ACTCGCTA
N718	GGAGCTAC
N719	GCGTAGTA
N720	CGGAGCCT
N721	TACGCTGC
N722	ATGCGCAG
N723	TAGCGCTC
N724	ACTGAGCG
N726	CCTAAGAC
N727	CGATCAGT
N728	TGCAGCTA
N729	TCGACGTC
S501	TAGATCGC
S502	CTCTCTAT
S503	TATCCTCT
S504	AGAGTAGA
S505	GTAAGGAG
S506	ACTGCATA
S507	AAGGAGTA
S508	CTAAGCCT
S510	CGTCTAAT
S511	TCTCTCCG
S513	TCGACTAG
S515	TTCTAGCT
S516	CCTAGAGT
S517	GCGTAAGA
S518	CTATTAAG
S520	AAGGCTAT
S521	GAGCCTTA
S522	TTATGCGA
"""
