import unittest
from io import StringIO

from sample_registry.illumina import IlluminaFastq


class IlluminaTests(unittest.TestCase):
    def test_illuminafastq(self):
        fastq_file = StringIO(
            u"@M03543:47:C8LJ2ANXX:1:2209:1084:2044 1:N:0:NNNNNNNN+NNNNNNNN")
        fastq_filepath = (
            "Miseq/160511_M03543_0047_000000000-APE6Y/Data/Intensities/"
            "BaseCalls/Undetermined_S0_L001_R1_001.fastq.gz")
        fastq_file.name = fastq_filepath
        fq = IlluminaFastq(fastq_file)

        self.assertEqual(fq.machine_type, "Illumina-MiSeq")
        self.assertEqual(fq.date, "2016-05-11")
        self.assertEqual(fq.lane, "1")
        self.assertEqual(fq.filepath, fastq_filepath)
