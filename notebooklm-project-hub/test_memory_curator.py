import unittest

import memory_curator as mc


class SemanticDedupTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            'title': 'Aislamiento de memoria multi-proyecto — capacity',
            'activity': 'Golden E2E multi-proyecto para validar aislamiento de memoria en el proyecto capacity.',
            'decision': 'El namespace capacity debe conservar únicamente memoria correspondiente a Capacity & Industrial Engineering y no mezclar eventos de otros proyectos.',
            'result': 'Se registró el marcador CAPACITY-ISO-20260927 para validación cruzada de aislamiento.',
            'next_step': '',
            'evidence': 'Prueba controlada de aislamiento entre capacity, excel-qa y production-program.',
            'tags': ['golden-e2e', 'isolation', 'capacity', 'CAPACITY-ISO-20260927'],
            'fingerprint': 'existing-fingerprint',
        }

    def test_exact_duplicate_still_matches(self):
        candidate = {key: value for key, value in self.original.items() if key != 'fingerprint'}
        result = mc._find_duplicate('capacity', candidate, [
            {
                **self.original,
                'fingerprint': mc._fingerprint('capacity', candidate),
            }
        ])
        self.assertIsNotNone(result)
        self.assertEqual(result['kind'], 'exact')
        self.assertEqual(result['semantic_score'], 1.0)

    def test_semantic_paraphrase_with_same_anchor_is_duplicate(self):
        candidate = {
            'title': 'Validación de aislamiento para capacity',
            'activity': 'Prueba Golden E2E entre múltiples proyectos para comprobar que la memoria de capacity permanece separada.',
            'decision': 'Mantener la memoria de capacity limitada al contexto de Capacity & Industrial Engineering, sin incorporar eventos de excel-qa ni production-program.',
            'result': 'Marcador CAPACITY-ISO-20260927 registrado para comprobar el aislamiento entre proyectos.',
            'next_step': '',
            'evidence': 'Ensayo controlado de separación de memoria entre capacity, excel-qa y production-program.',
            'tags': ['isolation', 'golden-e2e', 'capacity', 'CAPACITY-ISO-20260927'],
        }
        result = mc._find_duplicate('capacity', candidate, [self.original])
        self.assertIsNotNone(result)
        self.assertEqual(result['kind'], 'semantic')
        self.assertIn('capacity-iso-20260927', result['shared_anchors'])
        self.assertGreaterEqual(result['semantic_score'], mc.ANCHORED_DUPLICATE_THRESHOLD)

    def test_different_strong_anchor_is_not_duplicate(self):
        candidate = {
            'title': 'Aislamiento de memoria multi-proyecto — capacity',
            'activity': 'Golden E2E multi-proyecto para validar aislamiento de memoria en el proyecto capacity.',
            'decision': 'El namespace capacity debe conservar únicamente memoria correspondiente a Capacity & Industrial Engineering y no mezclar eventos de otros proyectos.',
            'result': 'Se registró el marcador CAPACITY-ISO-20260928 para una segunda validación de aislamiento.',
            'next_step': '',
            'evidence': 'Prueba controlada de aislamiento entre capacity, excel-qa y production-program.',
            'tags': ['golden-e2e', 'isolation', 'capacity', 'CAPACITY-ISO-20260928'],
        }
        self.assertIsNone(mc._find_duplicate('capacity', candidate, [self.original]))

    def test_related_but_distinct_unanchored_events_are_not_collapsed(self):
        previous = {
            'title': 'Validación de capacidad anual',
            'activity': 'Se validó el cálculo de capacidad anual para líneas de ensamble.',
            'decision': 'Mantener la lógica de turnos usada en el dashboard anual.',
            'result': 'El cálculo anual quedó validado para líneas de ensamble.',
            'next_step': '',
            'evidence': 'Comparación contra el tablero anual.',
            'tags': ['capacity', 'validation'],
            'fingerprint': 'previous',
        }
        candidate = {
            'title': 'Validación de capacidad de preparación',
            'activity': 'Se validó el cálculo de capacidad para procesos internos de preparación.',
            'decision': 'Mantener la lógica de turnos usada en el dashboard de preparación.',
            'result': 'El cálculo de preparación quedó validado para procesos internos.',
            'next_step': '',
            'evidence': 'Comparación contra el tablero de preparación.',
            'tags': ['capacity', 'validation'],
        }
        self.assertIsNone(mc._find_duplicate('capacity', candidate, [previous]))

    def test_trivial_score_remains_below_material_threshold(self):
        score, reasons = mc._score({
            'activity': 'revisé el proyecto un momento',
            'decision': '',
            'result': '',
            'evidence': '',
            'next_step': '',
            'tags': [],
        })
        self.assertEqual(score, 0)
        self.assertEqual(reasons, [])


if __name__ == '__main__':
    unittest.main()
