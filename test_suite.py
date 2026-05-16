# -*- coding: utf-8 -*-
"""
test_suite.py - Test suite for the Calistenia Telegram bot.

Runs 5 tests against real agents (Valeria + Analyst), then cleans up all
test data from Supabase regardless of test outcomes.
"""

import sys
import os
import traceback
import datetime
from pathlib import Path

# Force UTF-8 output so emojis / Spanish chars don't crash on Windows cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Make sure we run from the project root
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import database as db
from agents.orchestrator import Orchestrator

TEST_EMAIL = "test_suite@calistenia.test"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEP = "=" * 60


def section(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def ok(msg):
    print(f"  [PASS] {msg}")


def fail(msg, exc=None):
    print(f"  [FAIL] {msg}")
    if exc:
        traceback.print_exc()


results = {}  # test_name -> True/False


def run_test(name, fn):
    """Run a single test function, catch exceptions, record result."""
    print(f"\n>> {name}")
    try:
        fn()
        results[name] = True
    except AssertionError as e:
        fail(str(e))
        results[name] = False
    except Exception as e:
        fail(f"Unhandled exception: {type(e).__name__}: {e}", e)
        results[name] = False


# ===========================================================================
# SETUP
# ===========================================================================

section("SETUP - Creating / verifying test user profile")

existing = db.get_user_profile(user_email=TEST_EMAIL)
if existing:
    print(f"  User already exists: {existing.get('name')} -- will update profile.")

result = db.save_user_profile(
    user_email=TEST_EMAIL,
    name="Test User",
    age=30,
    weight=75,
    goals="Ganar musculo",
    injuries="",
    home_equipment="Mancuernas",
)
if result.get("status") == "ok":
    print("  Profile saved OK.")
else:
    print(f"  ERROR saving profile: {result}")
    sys.exit(1)

profile = db.get_user_profile(user_email=TEST_EMAIL)
print(f"  Profile loaded: {profile}")

# Create orchestrator once -- reuse across tests to maintain conversation history
orch = Orchestrator(user_email=TEST_EMAIL, profile=profile)


# ===========================================================================
# TEST 1 - RUTINA
# ===========================================================================

section("TEST 1 - RUTINA")

rutina_response = None


def test_rutina():
    global rutina_response
    msg = "Quiero hacer rutina en casa, tengo 40 minutos"
    print(f"  Sending: {msg!r}")
    response = orch.chat(msg)
    rutina_response = response
    print("\n  --- Valeria response (first 600 chars) ---")
    print(f"  {response[:600]}")
    print("  --- end ---\n")

    # 1a. Response must not be empty
    assert response and len(response.strip()) > 20, "Response is empty or too short"
    ok("Response is non-empty")

    # 1b. Must NOT contain raw JSON / function call syntax
    forbidden_patterns = ['"function_call"', '"tool_call"', '{"name":', '"exercises":[']
    for p in forbidden_patterns:
        assert p not in response, f"Response contains raw JSON/function syntax: {p!r}"
    ok("No raw JSON or function call syntax in response")

    # 1c. Must contain exercise indicators
    has_exercise_emoji = "\U0001f3cb️" in response  # weight lifter emoji
    has_exercise_words = any(w in response.lower() for w in [
        "series", "reps", "repeticion", "dominada", "flexion", "peso", "mancuerna",
        "curl", "press", "sentadilla", "ejercicio", "remo", "plancha",
    ])
    assert has_exercise_emoji or has_exercise_words, \
        "Response doesn't seem to contain an exercise list (no emoji or exercise words)"
    ok(f"Response contains exercise content (emoji={has_exercise_emoji}, words={has_exercise_words})")

    # 1d. Check that save_planned_workout was called
    planned = db.get_planned_workout(user_email=TEST_EMAIL)
    assert planned and planned.get("exercises"), \
        "save_planned_workout was NOT called -- no planned_workout found in DB for today"
    ok(f"save_planned_workout was called -- {len(planned['exercises'])} exercises saved in DB")


run_test("TEST 1 - RUTINA", test_rutina)


# ===========================================================================
# TEST 2 - REPORTE
# ===========================================================================

section("TEST 2 - REPORTE")

reporte_response = None


def test_reporte():
    global reporte_response
    msg = "Hice todo"
    print(f"  Sending: {msg!r}")
    response = orch.chat(msg)
    reporte_response = response
    print("\n  --- Valeria response (first 600 chars) ---")
    print(f"  {response[:600]}")
    print("  --- end ---\n")

    assert response and len(response.strip()) > 10, "Response is empty"
    ok("Response is non-empty")

    # 2a. Must contain confirmation checkmark or confirmation keywords
    has_check = "✅" in response  # checkmark emoji
    has_keywords = any(w in response.lower() for w in [
        "registr", "guard", "sesi", "completad", "perfecto", "anotado",
    ])
    assert has_check or has_keywords, \
        "Response doesn't contain confirmation checkmark or session keywords"
    ok(f"Response contains confirmation (checkmark={has_check}, keywords={has_keywords})")

    # 2b. Check DB for a session saved today
    today = datetime.date.today().isoformat()
    sessions = db.get_recent_sessions(limit=5, user_email=TEST_EMAIL)
    today_sessions = [s for s in sessions if s.get("date") == today]
    assert today_sessions, "No session was saved to DB for today after 'Hice todo'"
    ok(f"Session saved to DB -- session_id={today_sessions[0].get('id')}, "
       f"exercises={len(today_sessions[0].get('exercises', []))}")


run_test("TEST 2 - REPORTE", test_reporte)


# ===========================================================================
# TEST 3 - CONVERSACION
# ===========================================================================

section("TEST 3 - CONVERSACION")


def test_conversacion():
    # Record sessions count before
    sessions_before = db.get_recent_sessions(limit=20, user_email=TEST_EMAIL)

    msg = "Cuanto descanso debo tomar entre series de dominadas?"
    print(f"  Sending: {msg!r}")
    response = orch.chat(msg)
    print("\n  --- Valeria response (first 600 chars) ---")
    print(f"  {response[:600]}")
    print("  --- end ---\n")

    assert response and len(response.strip()) > 20, "Response is empty or too short"
    ok("Response is non-empty")

    # 3a. Should be a natural answer, not raw technical output
    forbidden_patterns = ['"function_call"', '{"exercises"', '"tool_call"']
    for p in forbidden_patterns:
        assert p not in response, f"Response contains raw JSON/tool syntax: {p!r}"
    ok("Response is natural text (no raw JSON/function syntax)")

    # 3b. Should mention rest/recovery concepts
    has_rest_content = any(w in response.lower() for w in [
        "descanso", "minuto", "segundo", "recuper", "rest", "pausa",
    ])
    assert has_rest_content, "Response doesn't seem to answer the rest question"
    ok("Response contains relevant rest/recovery content")

    # 3c. No new DB writes should have happened
    sessions_after = db.get_recent_sessions(limit=20, user_email=TEST_EMAIL)
    assert len(sessions_after) == len(sessions_before), \
        (f"A new session was unexpectedly saved "
         f"(before={len(sessions_before)}, after={len(sessions_after)})")
    ok("No new session saved to DB (correct for CONVERSACION)")


run_test("TEST 3 - CONVERSACION", test_conversacion)


# ===========================================================================
# TEST 4 - PROGRESO (Analyst)
# ===========================================================================

section("TEST 4 - PROGRESO (Analyst)")


def test_progreso():
    print("  Calling orchestrator.analyze_progress() ...")
    response = orch.analyze_progress()
    print("\n  --- Analyst response (first 600 chars) ---")
    print(f"  {response[:600]}")
    print("  --- end ---\n")

    assert response and len(response.strip()) > 30, "Analyst response is empty or too short"
    ok("Analyst returned a non-empty response")

    # Should not be the "no sessions" fallback
    assert "no hay sesiones" not in response.lower() and "no sessions" not in response.lower(), \
        "Analyst said there are no sessions, but we just saved one"
    ok("Analyst did not fall back to 'no sessions' message")

    # Should mention some progress/analysis content
    has_progress_words = any(w in response.lower() for w in [
        "sesi", "ejercicio", "progreso", "progres", "entren", "nalisis",
        "volumen", "series", "repet", "avance", "mejora", "recomend",
    ])
    assert has_progress_words, "Analyst response doesn't seem to contain progress analysis"
    ok("Analyst response contains progress/analysis content")


run_test("TEST 4 - PROGRESO (Analyst)", test_progreso)


# ===========================================================================
# TEST 5 - EXTRA: No technical leakage
# ===========================================================================

section("TEST 5 - EXTRA: No technical leakage in conversational response")


def test_no_leakage():
    msg = "Que musculo trabajan las flexiones de diamante?"
    print(f"  Sending: {msg!r}")
    response = orch.chat(msg)
    print("\n  --- Valeria response ---")
    print(f"  {response[:400]}")
    print("  --- end ---\n")

    assert response and len(response.strip()) > 10, "Response is empty"
    ok("Response is non-empty")

    # No raw JSON or Python code in response
    bad_patterns = [
        '{"name":', '"function_call"', 'def ', 'import ', 'save_planned_workout',
        'save_session(', '```json',
    ]
    for p in bad_patterns:
        assert p not in response, f"Response leaked technical content: {p!r}"
    ok("No technical leakage (no raw JSON, code, or function names)")

    # Should mention muscles
    has_muscle = any(w in response.lower() for w in [
        "tricep", "pecho", "deltoid", "musculo", "core",
        "anterior", "posterior", "hombro", "pectoral",
    ])
    assert has_muscle, "Response doesn't seem to answer the muscle question"
    ok("Response contains muscle/anatomy content")


run_test("TEST 5 - EXTRA: No leakage", test_no_leakage)


# ===========================================================================
# CLEANUP - Remove ALL test data from Supabase
# ===========================================================================

section("CLEANUP - Deleting all test data from Supabase")

cleanup_errors = []


def cleanup():
    supabase_client = db.supabase
    if not supabase_client:
        print("  ERROR: Supabase client not available -- skipping cleanup!")
        return

    # 1. Get all session IDs for this user
    sessions_res = supabase_client.table("sessions").select("id").eq("user_email", TEST_EMAIL).execute()
    session_ids = [s["id"] for s in (sessions_res.data or [])]
    print(f"  Sessions to delete: {len(session_ids)} -- ids={session_ids}")

    # 2. Delete exercises linked to those sessions
    if session_ids:
        for sid in session_ids:
            try:
                supabase_client.table("exercises").delete().eq("session_id", sid).execute()
            except Exception as e:
                cleanup_errors.append(f"exercises(session_id={sid}): {e}")
        print(f"  Exercises deleted for {len(session_ids)} session(s).")

    # 3. Delete sessions
    try:
        supabase_client.table("sessions").delete().eq("user_email", TEST_EMAIL).execute()
        print("  Sessions deleted.")
    except Exception as e:
        cleanup_errors.append(f"sessions: {e}")

    # 4. Delete planned_workouts
    try:
        supabase_client.table("planned_workouts").delete().eq("user_email", TEST_EMAIL).execute()
        print("  Planned workouts deleted.")
    except Exception as e:
        cleanup_errors.append(f"planned_workouts: {e}")

    # 5. Delete analyst_recommendations
    try:
        supabase_client.table("analyst_recommendations").delete().eq("user_email", TEST_EMAIL).execute()
        print("  Analyst recommendations deleted.")
    except Exception as e:
        cleanup_errors.append(f"analyst_recommendations: {e}")

    # 6. Delete user_profile
    try:
        supabase_client.table("user_profile").delete().eq("user_email", TEST_EMAIL).execute()
        print("  User profile deleted.")
    except Exception as e:
        cleanup_errors.append(f"user_profile: {e}")

    # Verify
    remaining_profile = db.get_user_profile(user_email=TEST_EMAIL)
    remaining_sessions = db.get_recent_sessions(limit=10, user_email=TEST_EMAIL)
    print(f"\n  Verification -- profile remaining: {bool(remaining_profile)}, "
          f"sessions remaining: {len(remaining_sessions)}")
    if not remaining_profile and not remaining_sessions:
        print("  [OK] DB cleaned successfully -- no test data remains.")
    else:
        print("  [WARN] Some data may still remain. Check manually.")

    if cleanup_errors:
        print(f"\n  [WARN] Cleanup errors: {cleanup_errors}")


cleanup()


# ===========================================================================
# SUMMARY
# ===========================================================================

section("SUMMARY")

total = len(results)
passed = sum(1 for v in results.values() if v)
failed = total - passed

print(f"\n  Tests run : {total}")
print(f"  Passed    : {passed}")
print(f"  Failed    : {failed}")
print()

for name, success in results.items():
    status = "[PASS]" if success else "[FAIL]"
    print(f"  {status}  {name}")

print()
if cleanup_errors:
    print(f"  [WARN] DB cleanup had {len(cleanup_errors)} error(s): {cleanup_errors}")
else:
    print("  [OK] DB cleanup: all test data removed from Supabase.")

print()
if failed == 0:
    print("  All tests passed!")
else:
    print(f"  {failed} test(s) failed. See details above.")
    sys.exit(1)
