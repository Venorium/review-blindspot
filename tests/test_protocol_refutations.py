"""Constructed counterexamples to overclaiming; never model observations."""
from itertools import product
import unittest

from rbs.metrics import joint_misses, summarize
from rbs.packets import MODE_DEMO


def observation(case, repeat, slot, missed, *, variant='faulty', arm='panel_blind',
                wrong_block=False):
    block = not missed or wrong_block
    return {
        'case_id': case, 'family_id': case, 'repeat': repeat, 'slot': slot,
        'variant': variant, 'arm_id': arm,
        'submission': {
            'execution': {
                'status': 'ok', 'input_tokens': None, 'output_tokens': None,
                'cost_usd': None, 'latency_seconds': None,
                'isolation_attested': False,
            },
            'review': {'verdict': 'request_changes' if block else 'approve'},
        },
        'annotation': {'target_detection': 'missed' if missed else 'detected'}
        if block and variant == 'faulty' else None,
    }


class ProtocolRefutationTests(unittest.TestCase):
    def test_reject_everything_cannot_masquerade_as_target_detection(self):
        rows = [observation('reject_all', 0, slot, True, variant=variant,
                            wrong_block=True)
                for variant in ('correct', 'faulty')
                for slot in ('r1', 'r2', 'r3')]
        result = summarize(rows, MODE_DEMO)
        arm = result['arms'][0]
        self.assertEqual(arm['unsafe_approval_bounds_all_scheduled'], [0, 0])
        self.assertEqual(arm['control_rejection_bounds_all_scheduled'], [1, 1])
        self.assertEqual(arm['target_recall_bounds'], [0, 0])
        self.assertEqual(arm['common_target_miss_bounds'], [1, 1])
        self.assertIsNone(arm['usage']['cost_usd']['known_sum'])
        self.assertIs(result['results_are_model_evidence'], False)

    def test_item_difficulty_produces_pooled_excess_without_within_case_dependence(self):
        rows = []
        # Exhaustive Cartesian products give exact independent distributions:
        # per-slot miss probability 1/4 for easy, 3/4 for hard (no sampling noise).
        for case, threshold in [('easy', 1), ('hard', 3)]:
            for repeat, (a, b) in enumerate(product(range(4), repeat=2)):
                rows.extend([observation(case, repeat, 'r1', a < threshold),
                             observation(case, repeat, 'r2', b < threshold)])
        for case in ('easy', 'hard'):
            within = joint_misses([r for r in rows if r['case_id'] == case])[0]
            self.assertEqual(within['excess_joint_miss'], 0)
        pooled = joint_misses(rows)[0]
        self.assertEqual(pooled['paired_known_trials'], 32)
        self.assertEqual(pooled['joint_miss_rate'], 5 / 16)
        self.assertEqual(pooled['product_of_pooled_marginals'], 1 / 4)
        self.assertEqual(pooled['excess_joint_miss'], 1 / 16)

    def test_positive_dependence_does_not_imply_no_panel_gain(self):
        # Each slot misses 4/8; both miss 3/8 (> 1/4 under independence).
        # The panel still detects 5/8, compared with 4/8 for the first slot.
        events = [(True, True)] * 3 + [(True, False), (False, True)] + [(False, False)] * 3
        rows = []
        for repeat, (a, b) in enumerate(events):
            rows.extend([observation('one_family', repeat, 'r1', a),
                         observation('one_family', repeat, 'r2', b),
                         observation('one_family', repeat, 'r1', a, arm='solo_blind')])
        result = summarize(rows, MODE_DEMO)
        arms = {arm['arm_id']: arm for arm in result['arms']}
        self.assertEqual(result['pairwise_joint_misses'][0]['excess_joint_miss'], 1 / 8)
        self.assertEqual(arms['panel_blind']['target_recall_bounds'], [5 / 8, 5 / 8])
        self.assertEqual(arms['solo_blind']['target_recall_bounds'], [1 / 2, 1 / 2])
        comparison = result['paired_comparisons'][0]
        self.assertEqual(comparison['mean_delta'], -1 / 8)
        self.assertEqual(comparison['family_count'], 1)
        self.assertIsNone(comparison['bootstrap_percentile_95'])
