class Tracer:
    @staticmethod
    def start_span(name: str, context: dict = None):
        # Placeholder
        return DummySpan()


class DummySpan:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def set_attribute(self, key, value): pass
    def add_event(self, name, attributes=None): pass