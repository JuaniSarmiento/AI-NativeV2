"""EPIC-20 demo: simulate a complete student cognitive session.

Generates real events through the actual API endpoints and WebSocket tutor,
then queries the trace endpoint to show the coherence metrics.

Usage:
    python scripts/epic20_demo.py
"""
import asyncio
import json
import sys
import time

import httpx
import websockets

BASE = "http://localhost:8001"
WS_BASE = "ws://localhost:8001"
EMAIL = "epic20-test@ainative.dev"
PASSWORD = "TestEpic20!"
EXERCISE_ID = "24ba7928-14ef-4059-a977-216423e4b2fe"


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as http:
        # --- Login ---
        print("1. Login...")
        r = await http.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
        token = r.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"   Token obtained.")

        # --- Read problem (triggers reads_problem event via outbox) ---
        print("\n2. Reading exercise (reads_problem)...")
        r = await http.get(f"/api/v1/student/exercises", headers=headers)
        exercises = r.json()["data"]
        ex = next((e for e in exercises if e["id"] == EXERCISE_ID), None)
        if ex:
            print(f"   Exercise: {ex['title']}")
        else:
            print(f"   Exercise {EXERCISE_ID} not found in student exercises!")
            return

        # --- Code snapshot 1 (initial attempt) ---
        print("\n3. Code snapshot 1 (initial code)...")
        code_v1 = "def division(a, b):\n    return a / b\n\nprint(division(10, 0))"
        r = await http.post(
            f"/api/v1/student/exercises/{EXERCISE_ID}/snapshot",
            headers=headers,
            json={"code": code_v1},
        )
        print(f"   Snapshot: {r.json()['status']}")

        # --- Run 1 (error) ---
        print("\n4. Code run 1 (ZeroDivisionError)...")
        r = await http.post(
            f"/api/v1/student/exercises/{EXERCISE_ID}/run",
            headers=headers,
            json={"code": code_v1},
        )
        run1 = r.json()["data"]
        print(f"   Status: {run1['status']}, stderr: {run1['stderr'][:80]}")

        # --- Tutor chat via WebSocket ---
        print("\n5. Connecting to tutor WebSocket...")
        ws_url = f"{WS_BASE}/ws/tutor/chat?token={token}"
        try:
            async with websockets.connect(ws_url) as ws:
                # Wait for connected message
                msg = json.loads(await ws.recv())
                print(f"   Connected: {msg.get('type')}")

                # --- Question 1: exploratory (N1 — comprensión) ---
                print("\n6. Tutor Q1: '¿qué significa ZeroDivisionError?' (exploratory, N1)")
                await ws.send(json.dumps({
                    "type": "chat",
                    "exercise_id": EXERCISE_ID,
                    "content": "no entiendo qué significa el ZeroDivisionError, me podés explicar?"
                }))
                assistant_response = await _collect_response(ws)
                print(f"   Tutor: {assistant_response[:150]}...")

                # --- Question 2: strategy (N2) ---
                print("\n7. Tutor Q2: '¿cómo hago para validar?' (exploratory, N2)")
                await ws.send(json.dumps({
                    "type": "chat",
                    "exercise_id": EXERCISE_ID,
                    "content": "cómo hago para validar que el divisor no sea cero antes de dividir?"
                }))
                assistant_response = await _collect_response(ws)
                print(f"   Tutor: {assistant_response[:150]}...")

                # --- Question 3: verification (verifier) ---
                print("\n8. Tutor Q3: '¿está bien mi solución?' (verifier, N4)")
                await ws.send(json.dumps({
                    "type": "chat",
                    "exercise_id": EXERCISE_ID,
                    "content": "está bien mi solución si uso try/except para capturar el ZeroDivisionError?"
                }))
                assistant_response = await _collect_response(ws)
                print(f"   Tutor: {assistant_response[:150]}...")

        except Exception as e:
            print(f"   WebSocket error: {e}")
            print("   Continuing without tutor chat...")

        # --- Code snapshot 2 (improved) ---
        print("\n9. Code snapshot 2 (improved with validation)...")
        code_v2 = (
            "def division(a, b):\n"
            "    if b == 0:\n"
            "        return 'Error: no se puede dividir por cero'\n"
            "    return a / b\n\n"
            "print(division(10, 2))\n"
            "print(division(10, 0))"
        )
        r = await http.post(
            f"/api/v1/student/exercises/{EXERCISE_ID}/snapshot",
            headers=headers,
            json={"code": code_v2},
        )
        print(f"   Snapshot: {r.json()['status']}")

        # --- Run 2 (success) ---
        print("\n10. Code run 2 (should succeed)...")
        r = await http.post(
            f"/api/v1/student/exercises/{EXERCISE_ID}/run",
            headers=headers,
            json={"code": code_v2},
        )
        run2 = r.json()["data"]
        print(f"    Status: {run2['status']}, stdout: {run2.get('stdout', '')[:80]}")

        # --- Run 3 (another success — verification) ---
        print("\n11. Code run 3 (verification run)...")
        r = await http.post(
            f"/api/v1/student/exercises/{EXERCISE_ID}/run",
            headers=headers,
            json={"code": code_v2},
        )
        run3 = r.json()["data"]
        print(f"    Status: {run3['status']}")

        # --- Wait for consumer to process events ---
        print("\n12. Waiting 8s for cognitive consumer to process events...")
        await asyncio.sleep(8)

        # --- Check cognitive sessions ---
        print("\n13. Checking cognitive sessions...")
        student_id = "67ce39c7-fd6a-457b-9778-17aa10812e90"
        r = await http.get(
            f"/api/v1/cognitive/sessions?student_id={student_id}&exercise_id={EXERCISE_ID}",
            headers=headers,
        )
        sessions_data = r.json()
        print(f"    Response: {json.dumps(sessions_data, indent=2)[:500]}")


async def _collect_response(ws) -> str:
    """Collect all tokens from the tutor until stream_end."""
    parts = []
    while True:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=30)
            msg = json.loads(raw)
            if msg.get("type") == "token":
                parts.append(msg.get("content", ""))
            elif msg.get("type") == "stream_end":
                break
            elif msg.get("type") == "error":
                print(f"   ERROR: {msg}")
                break
        except asyncio.TimeoutError:
            print("   TIMEOUT waiting for tutor response")
            break
    return "".join(parts)


if __name__ == "__main__":
    asyncio.run(main())
