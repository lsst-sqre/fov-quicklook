from hscmap import Window


def test_logger(w: Window):
    w.logger.info('info', js_alert=False, js_console=False)
    w.logger.warn('warn', js_alert=False, js_console=False)
    assert len(w.logger.buffer) == 2
    assert w.logger.buffer[0] == 'info'
    assert w.logger.buffer[1] == 'warn'

    for i in range(w.logger.max_length + 10):
        w.logger.info(f'info{i}', js_alert=False, js_console=False)
    assert len(w.logger.buffer) == w.logger.max_length
