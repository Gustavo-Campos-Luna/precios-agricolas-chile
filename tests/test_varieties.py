import unittest

import pandas as pd

from materias_primas_chile.varieties import Aliases, harmonize, load_aliases, load_species_map, variety_key

ALIASES = Aliases(pd.DataFrame([
    ["synonym", "exact", "sultanina", "thompsonseedless", ""],
    ["typo", "exact", "crimpsonseedless", "crimsonseedless", ""],
    ["family", "regex", "gala", "gala", ""],
    ["family", "regex", "reddelicious|redchief", "reddelicious", ""],
], columns=["policy", "match", "pattern", "target", "note"]))


class VarietyTests(unittest.TestCase):
    def test_key_ignores_case_accents_spaces_and_parentheses(self):
        self.assertEqual(variety_key("Red Globe"), variety_key("REDGLOBE"))
        self.assertEqual(variety_key("Corazón de Paloma (roja)"), "corazondepaloma")
        self.assertEqual(variety_key("Autumn Royal"), "autumnroyal")

    def test_unspecified_is_never_a_variety(self):
        for raw in ["Sin especificar", "Sin información", "", None, float("nan")]:
            self.assertEqual(variety_key(raw), "")

    def test_aliases_fix_typos_and_synonyms_but_families_only_in_group(self):
        data = pd.DataFrame({"variety": ["Sultanina", "Thompson seedless", "Crimpson Seedless", "Royal Gala",
                                         "Brookfield Gala", "Red Chief", "Lapins", "Sin especificar"]})
        out = harmonize(data, aliases=ALIASES).set_index("variety")
        self.assertEqual(out.loc["Sultanina", "variety_canonical"], out.loc["Thompson seedless", "variety_canonical"])
        self.assertEqual(out.loc["Crimpson Seedless", "variety_canonical"], "crimsonseedless")
        # los clones siguen distintos en canonical (fino) y se juntan solo en group (agregado)
        self.assertNotEqual(out.loc["Royal Gala", "variety_canonical"], out.loc["Brookfield Gala", "variety_canonical"])
        self.assertEqual(out.loc["Royal Gala", "variety_group"], "gala")
        self.assertEqual(out.loc["Brookfield Gala", "variety_group"], "gala")
        self.assertEqual(out.loc["Red Chief", "variety_group"], "reddelicious")
        self.assertEqual(out.loc["Lapins", "variety_group"], "lapins")
        self.assertEqual(out.loc["Sin especificar", "variety_group"], "")

    def test_original_column_is_preserved(self):
        data = pd.DataFrame({"variety": ["Red Globe"]})
        self.assertEqual(list(harmonize(data, aliases=ALIASES).variety), ["Red Globe"])

    def test_shipped_config_loads_and_species_map_is_unique(self):
        load_aliases()
        species = load_species_map()
        self.assertFalse(species.species.duplicated().any())
        self.assertIn(species.set_index("species").loc["Duraznero Tipo Conservero", "market_use"], {"processing"})


if __name__ == "__main__":
    unittest.main()
