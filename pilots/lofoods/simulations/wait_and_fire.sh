#!/bin/bash
# wait_and_fire.sh — Poll Anthropic API every 5 mins, auto-fire jobs when credits land.

PG="/Users/admin/Documents/Simulatte Projects/Persona Generator"
PERSONAS="$PG/pilots/lofoods/personas"
SPECS="$PG/pilots/lofoods/specs"
SIMS="$PG/pilots/lofoods/simulations"

echo "=== Credit Poller Started at $(date) ==="
echo "    Checking every 5 minutes..."

check_credits() {
    python3 -c "
import anthropic, sys
client = anthropic.Anthropic()
try:
    # Minimal API call — single token, just to test auth + credits
    r = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1,
        messages=[{'role':'user','content':'hi'}]
    )
    print('OK')
except anthropic.BadRequestError as e:
    if 'credit balance is too low' in str(e):
        print('NO_CREDITS')
    else:
        print('OK')  # different error = credits fine
except Exception as e:
    print(f'ERROR:{e}')
" 2>/dev/null
}

ATTEMPT=0
while true; do
    ATTEMPT=$((ATTEMPT + 1))
    STATUS=$(check_credits)
    echo "--- Check #${ATTEMPT} at $(date) — ${STATUS}"

    if [ "$STATUS" = "OK" ]; then
        echo ""
        echo "=== CREDITS LIVE — Firing jobs at $(date) ==="
        echo ""

        # ---------------------------------------------------------------
        # Job 1: Run 5 case study simulations (CS1, CS2, CS3, CS11, CS16)
        # ---------------------------------------------------------------
        echo ">>> Job 1: Case Study Simulations"
        cd "$PG" && python3 pilots/lofoods/simulations/run_case_studies.py 2>&1
        echo ">>> Job 1 complete at $(date)"
        echo ""

        # ---------------------------------------------------------------
        # Job 2: Regenerate C6–P4 cohorts (credits failed on first pass)
        # ---------------------------------------------------------------
        echo ">>> Job 2: Regenerating missing cohorts C6–P4"
        for ARCHETYPE in C6 C7 C8 C9 C10 C11 C12 C13 C14 C15 P1 P2 P3 P4; do
            echo "=== Starting ${ARCHETYPE} at $(date) ==="
            python3 "$PG/main.py" generate \
                --spec "$SPECS/spec_${ARCHETYPE}.json" \
                --count 10 \
                --domain lofoods_fmcg \
                --mode simulation-ready \
                --output "$PERSONAS/cohort_${ARCHETYPE}.json" \
                --sarvam \
                --skip-gates 2>&1 | tail -3
            echo "=== ${ARCHETYPE} done at $(date) ==="
        done

        echo ""
        echo ">>> Running attribute patch on all cohorts..."
        python3 "$PG/pilots/lofoods/patch_archetype_attributes.py" 2>&1
        echo ">>> All done at $(date)"
        exit 0
    fi

    # Wait 5 minutes before next check
    sleep 300
done
