from pathlib import Path
from unittest.mock import patch

from src.pipeline.research_pipeline import should_skip_step


@patch('src.pipeline.research_pipeline.ROOT', new=Path('/tmp/repo'))
def test_should_skip_step_when_outputs_newer_than_inputs(tmp_path):
    repo_root = Path('/tmp/repo')
    input_path = repo_root / 'data' / 'input.txt'
    output_path = repo_root / 'data' / 'output.txt'
    input_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text('in', encoding='utf-8')
    output_path.write_text('out', encoding='utf-8')
    output_path.touch()

    step = {
        'name': 'demo',
        'skip_if_outputs_fresh': True,
        'inputs': ['data/input.txt'],
        'outputs': ['data/output.txt'],
        'command': ['echo', 'demo'],
    }
    skip, reason = should_skip_step(step, context={'root': str(repo_root), 'run_id': 'x'})
    assert skip is True
    assert reason == 'outputs_newer_than_inputs'
