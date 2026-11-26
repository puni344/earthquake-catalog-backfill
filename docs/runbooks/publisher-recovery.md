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

To rehearse, run `python -m earthquake.verify --drill publish`. It creates its own database, operates four CLI reader loops and removes that database on exit. Missing phase coverage is reported as **NOT VERIFIED**. [Expected IDs, digests and observed recovery](../evidence/quake-publish.txt)
