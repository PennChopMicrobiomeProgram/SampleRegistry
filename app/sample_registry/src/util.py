import collections
import io
import itertools
import os

try:
    import itertools.izip as zip
except ImportError:
    pass


def key_by_attr(objs, attr):
    # Cannot use set() here, because objects might not be hashable.
    # Use list() instead, even though order is not important.
    obj_dict = collections.defaultdict(list)
    for obj in objs:
        val = getattr(obj, attr, None)
        obj_dict[val].append(obj)
    return obj_dict


def dict_from_eav(rows, entity_value):
    out = {}
    for entity, attr, val in rows:
        if entity == entity_value:
            out[attr] = val
    return out


def local_filepath(data_fp, local_mount, remote_mount):
    if local_mount is None:
        return data_fp
    if remote_mount is not None:
        data_fp = os.path.relpath(data_fp, remote_mount)
    return os.path.join(local_mount, data_fp.lstrip("/"))


def parse_fasta(f):
    f = iter(f)
    desc = next(f).strip()[1:]
    seq = io.StringIO()
    for line in f:
        line = line.strip()
        if line.startswith(">"):
            yield desc, seq.getvalue()
            desc = line[1:]
            seq = io.StringIO()
        else:
            seq.write(line)
    yield desc, seq.getvalue()


def _grouper(iterable, n):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3) --> ABC DEF
    args = [iter(iterable)] * n
    return zip(*args)


def parse_fastq(f):
    for desc, seq, _, qual in _grouper(f, 4):
        desc = desc.rstrip()[1:]
        seq = seq.rstrip()
        qual = qual.rstrip()
        yield desc, seq, qual


class FastaRead(object):
    def __init__(self, read):
        self.desc, self.seq = read


class FastqRead(object):
    def __init__(self, read):
        self.desc, self.seq, self.qual = read


AMBIGUOUS_BASES = {
    "T": "T",
    "C": "C",
    "A": "A",
    "G": "G",
    "R": "AG",
    "Y": "TC",
    "M": "CA",
    "K": "TG",
    "S": "CG",
    "W": "TA",
    "H": "TCA",
    "B": "TCG",
    "V": "CAG",
    "D": "TAG",
    "N": "TCAG",
    }

# Ambiguous base codes for all bases EXCEPT the key
AMBIGUOUS_BASES_COMPLEMENT = {
    "T": "V",
    "C": "D",
    "A": "B",
    "G": "H",
    }


def deambiguate(seq):
    nt_choices = [AMBIGUOUS_BASES[x] for x in seq]
    return ["".join(c) for c in itertools.product(*nt_choices)]

COMPLEMENT_BASES = {
    "T": "A",
    "C": "G",
    "A": "T",
    "G": "C",
    }

def reverse_complement(seq):
    rc = [COMPLEMENT_BASES[x] for x in seq]
    rc.reverse()
    return ''.join(rc)
