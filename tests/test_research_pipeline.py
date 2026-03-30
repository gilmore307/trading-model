from src.pipeline.anomaly_rules import evaluate_rules
from src.pipeline.research_pipeline import build_context


def test_build_context_expands_artifacts_with_run_id():
    config = {
        'artifacts': {
            'manifest': 'logs/pipeline/runs/{run_id}/manifest.json',
            'labels': 'data/derived/labels.jsonl',
        }
    }
    context = build_context(config, 'research_20260327T000000Z')
    assert context['run_id'] == 'research_20260327T000000Z'
    assert context['manifest'].endswith('/research_20260327T000000Z/manifest.json')
    assert context['labels'] == 'data/derived/labels.jsonl'


def test_evaluate_rules_warns_on_cluster_dominance_and_low_spread(tmp_path):
    labels_summary = tmp_path / 'labels_summary.json'
    labels_summary.write_text('{"cluster_counts":[{"cluster_id":3,"row_count":90},{"cluster_id":1,"row_count":10}]}', encoding='utf-8')
    evaluation = tmp_path / 'evaluation.json'
    evaluation.write_text('{"summary":{"weighted_avg_cluster_spread":0.00001,"cluster_count":2}}', encoding='utf-8')
    config = {
        'artifacts': {
            'labels_summary': str(labels_summary),
            'unsupervised_evaluation': str(evaluation),
        }
    }
    result = evaluate_rules(config)
    assert result['status'] == 'alert'
    rules = {row['rule'] for row in result['alerts']}
    assert 'cluster_dominance_high' in rules
    assert 'weighted_spread_low' in rules
    assert 'cluster_count_too_low' in rules
