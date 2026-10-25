"""Startup entrypoint: checks for an existing instance BEFORE importing Gradio."""
from audioforge.single_instance import run_single_instance


def start(ready_callback):
    from app import main  # Heavy UI/AI dependencies are loaded only once.
    main(ready_callback)


if __name__ == "__main__":
    raise SystemExit(run_single_instance(start))
