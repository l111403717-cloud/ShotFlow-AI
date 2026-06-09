class AppContext:
    def __init__(self, root, config, global_log, safe_after_fn):
        self.root = root
        self.config = config
        self.global_log = global_log
        self.safe_after = safe_after_fn
        self.pages = {}
        # Used for "circuit breaker" variables etc
        self.bailian_circuit_open = False

    def log(self, msg):
        import time
        ts = time.strftime("%H:%M:%S")
        self.safe_after(lambda: self.global_log.append(f"[{ts}] {msg}"))

    def get_page(self, name):
        return self.pages.get(name)

    def register_page(self, name, page):
        self.pages[name] = page
