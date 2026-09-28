# Camofox vault-fill fix (optional extra)

An optional Hermes Agent patch, unrelated to Discord. It makes Hermes Vault
autofill work when the browser backend is Camofox. The pack installer and safe
updater only apply `patches/*.patch`, so this file is never applied for you.

Upstream tracking issue: [NousResearch/hermes-agent#126247](https://github.com/NousResearch/hermes-agent/issues/126247).
Drop this patch once upstream supports Camofox vault injection.

## Symptom

With `browser.cloud_provider: camofox`, `browser_navigate`, `browser_snapshot`
and `browser_console` see the login page, but `browser_vault_fill` refuses:

```text
origin_mismatch: current page origin (chrome://new-tab-page) does not match the vault item's bound origin(s)
```

`browser_vault_save_login` and `browser_vault_enter_code` fail the same way.

## Cause

`tools/browser_vault_tool.py` evaluates page JavaScript only through the CDP
supervisor. Camofox is Firefox-based and has no CDP endpoint, so the vault tool
asks agent-browser for a `cdp-url`. That starts a separate packaged Chromium
whose only tab is `chrome://new-tab-page`. The origin check reads that blank
Chromium tab instead of the Camofox tab, and correctly refuses to fill.

## What the patch changes

Only in Camofox mode (`_is_camofox_mode()` is true):

- Inspection and origin reads (`_eval_js`) go through Camofox's
  `POST /tabs/{tabId}/evaluate`, the same route `browser_console` already uses.
- The secret-bearing fill (`_eval_js_secret`) uses the same route.
- `_focus_bound_origin` returns early, so no stray Chromium is started.

The CDP and agent-browser paths are unchanged. The exact-origin check, the
in-script origin re-assertion, and result redaction all still run.

## Security notes

- The fill expression, which contains the secret, travels as a JSON request
  body to the Camofox server. It never enters subprocess argv.
- The stock Camofox server logs only the result type for `evaluate`. Camofox
  plugins can subscribe to the `tab:evaluate` event, which carries the
  expression, so audit any third-party Camofox plugins you enable.
- Run Camofox on loopback, the default. If `CAMOFOX_URL` points at another
  host, the password crosses the network in that request body.

## Apply

From your Hermes checkout:

```bash
cd ~/.hermes/hermes-agent
git apply --check /path/to/camofox-vault-fill.patch
git apply /path/to/camofox-vault-fill.patch
hermes gateway restart
```

Verify the route is active under your config:

```bash
cd ~/.hermes/hermes-agent
set -a; . ~/.hermes/.env; set +a
./venv/bin/python -c "from tools import browser_vault_tool as v; print(v._camofox_active())"
```

`True` means vault fills now target the Camofox tab.

## Revert

```bash
cd ~/.hermes/hermes-agent
git apply -R /path/to/camofox-vault-fill.patch
hermes gateway restart
```

## After Hermes updates

A Hermes update can conflict with local source edits or discard them.
Re-run the `git apply --check` step after each update. If the check fails because
upstream changed the file, look at issue #126247 before re-porting.

## Compatibility

- Built and run against Hermes Agent `ffe5cf049d` (2026-09-26). Verified end
  to end on a Camofox gateway: a login fill that had failed with
  `origin_mismatch` succeeded after the patch and a gateway restart.
- `git apply --check` is clean against upstream `main` at `dd3ba4b4b8d6` (2026-09-28).
