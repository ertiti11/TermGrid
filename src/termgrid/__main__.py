__all__ = ["main"]
__version__ = "0.1.0"

def main():
    from .app import ServerTUI
    ServerTUI().run()
