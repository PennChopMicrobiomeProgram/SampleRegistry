import io
from src.sample_registry.mapping import SampleTable


NORMAL_TSV = """\
SampleID	BarcodeSequence	HostSpecies	SubjectID
S1	GCCT	Human	Hu23
S2	GCAT	NA	NA
"""
NEXTERA_TSV = """\
SampleID	external_id_tube	SampleType	SubjectID	HostSpecies	host_strain	study_day	study_group	SL_or_LL	study_sample	dna_location	dna_concentration_ng/ul	date_extracted	index_set	avg_frag_size_bp	FragA_nM	PG_lib_conc	barcode_index_fwd	barcode_index_rev	flow_cell_lane	flow_cell_id	run_start_date
HC.1.1.0.NA.1	1	Feces	1	Rat	sprague.dawley	0	HC	NA	1	original plate	36.73	20151203	B	252	13.675	3.42466	N716	S502	"5,6,7,8"	C8DEKANXX	20151209
HC.2.2.0.NA.1	2	Feces	2	Rat	sprague.dawley	0	HC	NA	1	original plate	0.97	20151203	B	213	5.33	0.67984	N716	S503	"5,6,7,8"	C8DEKANXX	20151209
HC.3.3.0.NA.1	3	Feces	3	Rat	sprague.dawley	0	HC	NA	1	original plate	0.84	20151203	B	327	8.035	1.41526	N716	S505	"5,6,7,8"	C8DEKANXX	20151209
"""

recs = [
    {
        "SampleID": "S1",
        "BarcodeSequence": "GCCT",
        "HostSpecies": "Human",
        "SubjectID": "Hu23",
    },
    {
        "SampleID": "S2",
        "BarcodeSequence": "GCAT",
    },
]


def test_write():
    t = SampleTable(recs)
    output_file = io.StringIO()
    t.write(output_file)
    assert output_file.getvalue() == NORMAL_TSV


def test_parse():
    input_file = io.StringIO(NORMAL_TSV)
    t = SampleTable.load(input_file)
    assert t.recs == recs


def test_validate():
    t = SampleTable(recs)
    assert t.validate() is None


def test_validate_with_duplicated_sample_name():
    recs[1]["SampleID"] = "S1"
    t = SampleTable(recs)
    try:
        t.validate()
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_look_up_nextera_barcodes():
    input_file = io.StringIO(NEXTERA_TSV)
    t = SampleTable.load(input_file)
    t.look_up_nextera_barcodes()
    assert t.recs[1]["BarcodeSequence"] == "ACTCGCTA-TATCCTCT"
    assert t.validate() == None
