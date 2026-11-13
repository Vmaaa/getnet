import argparse
import json
import sys
import time
import urllib.request

SCENARIOS = [
    ("What's the difference between the Get Clássica and the Get Smart?", "cliente1988", "knowledge"),
    ("What's the weather forecast in Porto Alegre tomorrow?", "cliente1988", "knowledge"),
    ("When will the money from yesterday's sales be deposited?", "cliente1988", "support"),
    ("Do I need a bank account to receive my sales via Pix?", "cliente1988", "knowledge"),
    ("My card machine won't connect to the internet, what should I do?", "cliente1988", "support"),
    ("How does receivables advance (antecipação) work with Getnet?", "cliente1988", "knowledge"),
    ("What's the euro exchange rate today?", "cliente1988", "knowledge"),
    ("My card machine is showing a transaction decline error.", "cliente1988", "support"),
    ("How many installments can I split a sale into with the crediário?", "cliente1988", "knowledge"),
    ("Can I sell through WhatsApp using the Payment Link?", "cliente1988", "knowledge"),
]

VALID_TOOLS = {"get_user_profile", "get_transactions", "get_device_status"}


def post_chat(base_url: str, message: str, user_id: str, timeout: int) -> tuple[int, dict]:
    payload = json.dumps({"message": message, "user_id": user_id}).encode()
    request = urllib.request.Request(
        f"{base_url}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read())


def check(body: dict, expected: str) -> list[str]:
    failures = []
    for key in ("status", "answer", "citations", "tools_used", "agent_trace", "session_id"):
        if key not in body:
            failures.append(f"missing key {key}")
            return failures
    if len(body["answer"].split()) < 3:
        failures.append("answer too short")
    refs = [c["ref"] for c in body["citations"]]
    if refs and refs != list(range(1, len(refs) + 1)):
        failures.append(f"refs not contiguous: {refs}")
    for citation in body["citations"]:
        if not citation.get("text") or not citation.get("url") or not citation.get("title"):
            failures.append("citation missing text/url/title")
            break
    if expected == "knowledge" and not body["citations"]:
        failures.append("expected citations for knowledge scenario")
    if expected == "support":
        if not body["tools_used"]:
            failures.append("expected tools_used for support scenario")
        invalid = [t for t in body["tools_used"] if t not in VALID_TOOLS]
        if invalid:
            failures.append(f"invalid tools: {invalid}")
    for entry in body["agent_trace"]:
        if entry["agent"] not in ("knowledge", "support"):
            failures.append(f"invalid trace agent: {entry['agent']}")
            break
    attempts = [entry["attempt"] for entry in body["agent_trace"]]
    if attempts != sorted(attempts):
        failures.append(f"trace attempts unordered: {attempts}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    rows = []
    exit_code = 0
    for message, user_id, expected in SCENARIOS:
        start = time.monotonic()
        body: dict = {}
        failures: list[str] = []
        try:
            status, body = post_chat(args.base_url, message, user_id, args.timeout)
            if status != 200:
                failures.append(f"http {status}")
            else:
                failures = check(body, expected)
            if args.verbose:
                print(json.dumps(body, ensure_ascii=False, indent=2))
        except Exception as exc:
            failures.append(f"request failed: {exc}")
        elapsed = time.monotonic() - start
        rows.append((message, body, not failures, elapsed, failures))
        if failures:
            exit_code = 1

    print()
    print(f"{'RESULT':<6} | {'STATUS':<7} | {'CITES':<5} | {'TOOLS':<20} | {'TIME':>6} | SCENARIO")
    for message, body, ok, elapsed, failures in rows:
        mark = "" if ok else " -> " + "; ".join(failures)
        tools = ",".join(body.get("tools_used", []))[:20]
        print(
            f"{'PASS' if ok else 'FAIL':<6} | {body.get('status', '-'):<7} | "
            f"{len(body.get('citations', [])):<5} | {tools:<20} | {elapsed:5.1f}s | {message[:48]}{mark}"
        )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
