# GSMA Open Gateway Helm Chart

## CAPIF integration

Set `capif.enabled=true` to have the gateway onboard itself as a CAPIF provider and publish the CAMARA APIs it exposes to CAPIF (mirrors `gsma_apis_protected_by_capif=true` in `config.toml`). Once enabled, callers of those APIs must present a valid CAPIF-issued invoker access token.

The gateway generates its onboarding certificates at runtime under `app/capif/certificates/<capif.username>/`. Since there's no shared filesystem across nodes by default, those certs are persisted across restarts/rollouts via a `hostPath` volume (`capif.hostPath`, default `/mnt/gateway-capif-certs`). **This means the pod must land on the same node across restarts**, or it will be re-onboarded as a new provider and rejected by CAPIF core with "Already registered service with same api name". Set `.Values.nodeSelector` (e.g. `{"kubernetes.io/hostname": "<node>"}`) to pin it there — this matters most on multi-node clusters; on a single-node dev cluster it's a no-op.

Also set `capif.host`, `capif.registerHost`, `capif.httpsPort`, `capif.registerPort`, `capif.username` and `capif.password` to match your CAPIF core deployment.

This is independent of `gatewayConfig.nef.auth_mode: capif`, which controls whether the gateway onboards as a CAPIF *invoker* to reach NEF — both can be enabled at once and share the same `capif.*` connection settings (`host`, `registerHost`, `httpsPort`, `registerPort`), but only `capif.enabled` (the provider side) needs the hostPath volume, since invoker certs currently aren't persisted.

### mTLS enforcement (nginx)

`nginx.enabled` (default `true`) deploys an `nginx` reverse proxy in front of the gateway that terminates TLS. When `capif.enabled` is also `true`, it additionally enforces the mutual TLS CAPIF core expects: it serves the CAPIF-issued AEF certificate (`aef-1.crt` / `AEF-1_private_key.key`) and requires callers to present a client certificate signed by the CAPIF-issued CA (`ca.crt`), rejecting the request with a `403` otherwise. This is on top of, not instead of, the gateway's own JWT verification of the CAPIF-issued invoker access token.

nginx and the gateway share the CAPIF onboarding certs through the same `capif.hostPath` volume described above, so nginx is subject to the same node-pinning requirement. An init container on the nginx pod waits for the AEF certs to appear on that shared volume before nginx starts (they're written asynchronously by the gateway during onboarding).

When `capif.enabled` is `false`, nginx still runs (terminating TLS with a self-signed cert, no client-cert verification) for parity with the non-CAPIF dev/test setup NEF_emulator also falls back to.
