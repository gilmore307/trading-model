from src.runner.test_mode import split_test_report


def test_split_test_report_moves_steps_to_detail_only():
    summary = {
        'runs': [
            {
                'steps': [{'step': 'a'}],
                'final_positions': [{'status': 'closed'}, {'status': 'open'}],
            }
        ]
    }
    summary_view, detail = split_test_report(summary)
    assert 'steps' not in summary_view['runs'][0]
    assert summary_view['runs'][0]['step_count'] == 1
    assert summary_view['runs'][0]['final_open_positions'] == [{'status': 'open'}]
    assert detail['runs'][0]['steps'] == [{'step': 'a'}]
