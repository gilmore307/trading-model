from pathlib import Path


def test_fresh_reset_preserves_daemon_pid(tmp_path):
    service = tmp_path / 'service'
    service.mkdir(parents=True)
    (service / 'daemon.pid').write_text('123\n')
    (service / 'daemon.log').write_text('x')
    removed = []
    for child in sorted(service.iterdir()):
        if child.name == 'daemon.pid':
            continue
        child.unlink()
        removed.append(child.name)
    assert (service / 'daemon.pid').exists()
    assert removed == ['daemon.log']
