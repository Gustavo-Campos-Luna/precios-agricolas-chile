import unittest

from materias_primas_chile import ine

SAMPLE = """DATAFLOW,AREA_REF,FREQ,INDICADOR,UNIDAD,TIME_PERIOD,OBS_VALUE,OBS_STATUS
X,_T,M,ICLEMP2023,IX,2010-M02,44.1,
X,_T,M,ICLEMP2023,IX,2010-M01,43.9,
X,_T,M,ICLEMP2023,VAR12,2010-M01,2.2,
X,_T,M,ICLEMP2023,IX,2010-M03,,
"""


class ParseTests(unittest.TestCase):
    def test_keeps_only_index_levels_sorted_by_month_and_drops_empty_observations(self):
        t = ine.parse_sdmx_csv(SAMPLE)
        self.assertEqual(t["value"].tolist(), [43.9, 44.1])
        self.assertEqual([d.strftime("%Y-%m") for d in t["month"]], ["2010-01", "2010-02"])

    def test_unit_none_keeps_every_unit(self):
        self.assertEqual(len(ine.parse_sdmx_csv(SAMPLE, unit=None)), 3)

    def test_unparseable_periods_are_dropped(self):
        t = ine.parse_sdmx_csv(SAMPLE.replace("2010-M02", "2010-Q1"))
        self.assertEqual(len(t), 1)


if __name__ == "__main__":
    unittest.main()
