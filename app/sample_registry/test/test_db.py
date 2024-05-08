import unittest

from sample_registry.db import RegistryDatabase

class RegistryDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = RegistryDatabase(":memory:")
        self.db.create_tables()
        self.run = (
            u"2015-10-11", u"HiSeq", u"Nextera XT", 1,
            u"run_file.fastq", u"Bob's run",
            )
        self.run_acc = self.db.register_run(*self.run)
        self.sample_bcs = [
            ("Sample1", "ABC"),
            ("Sample2", "DEF"),
            ("My.Sample3", "GHI"),
            ]
        self.single_sample = self.sample_bcs[0]
        self.annotations = {
            "SampleType": "Oral swab",
            "SubjectID": "Subj23",
            "study_group": "Healthy",
            "study_day": "1",
            }

    def test_register_run(self):        
        self.assertEqual(self.run_acc, 1)
        self.assertTrue(self.db.query_run_exists(self.run_acc))
        obs_fp = self.db.query_run_file(self.run_acc)
        self.assertEqual("run_file.fastq", obs_fp)
        # Registering the run twice should raise an error
        self.assertRaises(ValueError, self.db.register_run, *self.run)

    def test_query_run_exists(self):
        self.assertTrue(self.db.query_run_exists(1))

    def test_register_samples(self):
        # Here, accessions given by database cursor.  In other tests,
        # we double-check that we can actually find the samples in a
        # query
        registered_accessions = self.db.register_samples(
            1, self.sample_bcs)
        self.assertEqual(registered_accessions, [1, 2, 3])
        # Registering the samples again should raise an error
        self.assertRaises(
            ValueError, self.db.register_samples, 1, self.sample_bcs)

    def test_query_barcoded_sample_accessions(self):
        self.db.register_samples(1, self.sample_bcs)
        self.assertEqual(
            self.db.query_barcoded_sample_accessions(1, self.sample_bcs),
            [1, 2, 3])

    def test_query_sample_accessions(self):
        self.db.register_samples(1, self.sample_bcs)
        self.assertEqual(
            self.db.query_sample_accessions(1), [1, 2, 3])

    def test_query_sample_barcodes(self):
        self.db.register_samples(1, self.sample_bcs)
        self.assertEqual(self.db.query_sample_barcodes(1), self.sample_bcs)

    def test_remove_samples(self):
        self.db.register_samples(1, self.sample_bcs)
        self.db.remove_samples([1, 2, 3])
        self.assertEqual(self.db.query_sample_accessions(1), [])

    def test_register_and_remove_annotations(self):
        sample_accessions = self.db.register_samples(1, self.sample_bcs)
        for acc in sample_accessions:
            ann = [(acc, k, v) for k, v in self.annotations.items()]
            self.db.register_annotations(ann)

        self.db.remove_annotations(sample_accessions)
        for acc in sample_accessions:
            self.assertEqual(
                self.db.query_sample_annotations(acc), {})

    def test_register_and_query_annotations(self):
        self.db.register_samples(1, [("Sample1", "GGCCTT")])
        ann = [(1, k, v) for k, v in self.annotations.items()]
        self.db.register_annotations(ann)
        self.assertEqual(
            self.db.query_sample_annotations(1), self.annotations)

    def test_collect_standard_annotations(self):
        a = [
            (1, "SampleType", "a"),
            (1, "HostSpecies", "b"),
            (2, "SubjectID", "c"),
            ]
        obs = RegistryDatabase._collect_standard_annotations(a)
        self.assertEqual(obs, {1: ["a", None, "b"], 2: [None, "c", None]})


if __name__ == "__main__":
    unittest.main()
