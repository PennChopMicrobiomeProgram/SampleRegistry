from io import StringIO
from src.sample_registry.illumina import IlluminaFastq


def test_illuminafastq():
    fastq_file = StringIO(
        "@M03543:47:C8LJ2ANXX:1:2209:1084:2044 1:N:0:NNNNNNNN+NNNNNNNN"
    )
    fastq_filepath = (
        "Miseq/160511_M03543_0047_000000000-APE6Y/Data/Intensities/"
        "BaseCalls/Undetermined_S0_L001_R1_001.fastq.gz"
    )
    fastq_file.name = fastq_filepath
    fq = IlluminaFastq(fastq_file)

    assert fq.machine_type == "Illumina-MiSeq"
    assert fq.date == "2016-05-11"
    assert fq.lane == "1"
    assert fq.filepath == fastq_filepath
