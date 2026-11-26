# Recover a stopped catalog publisher

Use this procedure for the frozen October fixture on the local Windows SQLite store. A publisher can exit after issuing its pointer update and before committing. A successful SQL statement or a process exit alone cannot establish which publication a reader sees.

1. Identify the affected database from the publisher log. Set the PowerShell variable `$db` to its absolute path. Preserve the database and its journal files. Confirm the affected publisher has exited and record the time, PID and last acknowledged action.
2. From the checkout root run `python -m earthquake.history --db $db current` and `python -m earthquake.history --db $db list`. Record the exit codes, scope and current ID. In the M06 pre-commit incident the expected current scope at this point is 1–3 October. An unknown ID, unexpected scope or digest mismatch needs investigation before retry.
3. Verify the returned records against the independent whole-week oracle. The following PowerShell pipeline checks the reported ID, count and digest for the actual CLI rows. A failing check exits nonzero.

   ```powershell
   python -m earthquake.history --db $db current | python -c "import json,sys; from earthquake.publish_drill import check,oracles; r=check(json.load(sys.stdin),{o['id']:o for o in oracles()}); print(r); sys.exit(r['status']!='success')"
   ```

4. If the shorter extract is still current and the longer one is due, retry on the same database through the normal publisher. It revalidates the source bodies, daily checkpoints and staged rows. Record its exit code and emitted ID.

   ```powershell
   python -c "import sys; from pathlib import Path; from earthquake.history import publish; print(publish(Path(sys.argv[1]),7))" $db
   ```

5. Repeat the current-row check in a fresh CLI process and require the 1–7 October ID. For each historic ID, replace `current` in the pipeline with `get <publication-id>` and verify the returned ID equals the requested one. Preserve the elapsed time to the first verified new read and the final results for both scopes.

For an interrupted acquisition, take the acquisition ID from the printed staging path. Run `python -m earthquake.verify --drill acquire --resume ACQUISITION_ID` against the same local state. A fresh invocation without the ID starts a separate capture. The collector holds a per-run SQLite writer lock. If another collector owns it, wait for that process to finish.

Each accepted response has a local receipt binding the run ID, exact query, attempts, HTTP outcome, length, SHA-256, count and staging directory. The collector installs that receipt before promoting the exported blob. Resume verifies receipted staging bytes and any installed copy. A missing receipt requires a new response from the same URL. A conflicting receipt or damaged receipted body stops completion. Retain the run for diagnosis. Older interrupted runs without receipts need fresh requests. Receipts assume trusted local state. The drill covers worker termination.

Select a fixture only after its manifest passes `python -m earthquake.verify --drill acquire --offline PATH_TO_MANIFEST`. Following a staging-write denial or source discrepancy, verify the prior current ID and resolve the failure before retry. [Original injections](../evidence/M07-failures.txt) and [restart remediation](../evidence/M07-orphan-remediation.txt)
