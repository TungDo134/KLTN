import os
import threading
import time

from dotenv import load_dotenv
from langchain_groq import ChatGroq


load_dotenv()


MODEL_NAME = "llama-3.3-70b-versatile"
PROMPT = "Tra loi ngan gon bang tieng Viet: 2 + 2 bang may?"


def _print_elapsed_until_done(label: str, started_at: float, done: threading.Event):
    while not done.is_set():
        time.sleep(10)
        if not done.is_set():
            elapsed = time.perf_counter() - started_at
            print(f"[{label}] still waiting... {elapsed:.2f}s")


def _start_progress(label: str, started_at: float) -> tuple[threading.Event, threading.Thread]:
    done = threading.Event()
    thread = threading.Thread(
        target=_print_elapsed_until_done,
        args=(label, started_at, done),
        daemon=True,
    )
    thread.start()
    return done, thread


def _test_invoke(client: ChatGroq):
    print("\n[1] Testing Groq invoke...")
    started_at = time.perf_counter()
    done, progress_thread = _start_progress("groq invoke", started_at)
    try:
        response = client.invoke([{"role": "user", "content": PROMPT}])
        elapsed = time.perf_counter() - started_at
        print(f"OK Groq invoke in {elapsed:.2f}s")
        print("Response:", response.content)
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        print(f"FAILED Groq invoke after {elapsed:.2f}s")
        print(f"Error: {type(exc).__name__}: {repr(exc)}")
        return False
    finally:
        done.set()
        progress_thread.join(timeout=1)

    return True


def _test_stream(client: ChatGroq):
    print("\n[2] Testing Groq stream...")
    started_at = time.perf_counter()
    done, progress_thread = _start_progress("groq stream", started_at)
    chunks = []
    first_token_at = None

    try:
        for chunk in client.stream([{"role": "user", "content": PROMPT}]):
            token = getattr(chunk, "content", "")
            if token:
                if first_token_at is None:
                    first_token_at = time.perf_counter() - started_at
                    print(f"First stream token after {first_token_at:.2f}s")
                chunks.append(token)

        elapsed = time.perf_counter() - started_at
        print(f"OK Groq stream in {elapsed:.2f}s")
        print("Stream response:", "".join(chunks))
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        print(f"FAILED Groq stream after {elapsed:.2f}s")
        print(f"Error: {type(exc).__name__}: {repr(exc)}")
    finally:
        done.set()
        progress_thread.join(timeout=1)


def main():
    print("=" * 60)
    print("GROQ llama-3.3-70b-versatile HEALTH CHECK")
    print("=" * 60)
    print(f"Model   : {MODEL_NAME}")
    print("Timeout : disabled")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("FAILED: GROQ_API_KEY is not set.")
        return

    client = ChatGroq(
        model=MODEL_NAME,
        api_key=api_key,
        temperature=0.2,
        max_tokens=256,
    )

    if _test_invoke(client):
        _test_stream(client)


if __name__ == "__main__":
    main()
