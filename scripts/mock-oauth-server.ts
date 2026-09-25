/**
 * Mock OAuth Server para desarrollo local de SIGED
 * Simula el servicio OAuth de Manus para no depender de un servidor externo.
 *
 * Endpoints:
 *   GET  /app-auth                                          → página de login falsa
 *   POST /webdev.v1.WebDevAuthPublicService/ExchangeToken   → devuelve tokens
 *   POST /webdev.v1.WebDevAuthPublicService/GetUserInfo     → devuelve info del usuario
 *   POST /webdev.v1.WebDevAuthPublicService/GetUserInfoWithJwt → idem con JWT
 */

import express from "express";

const app = express();
app.use(express.json());

const PORT = 3001;

// Usuario mock para desarrollo
const MOCK_USER = {
  openId: "dev-user-001",
  projectId: "dev-app",
  name: "Dr. Samudio (Dev)",
  email: "dev@siged.local",
  platform: "email",
  loginMethod: "email",
};

// ─── GET /app-auth ──────────────────────────────────────────
// Página de login falsa: muestra un botón que redirige de vuelta
// al callback del servidor principal con un code inventado.
app.get("/app-auth", (req, res) => {
  const { appId, redirectUri, state, type } = req.query as Record<string, string>;

  if (!redirectUri) {
    res.status(400).send("redirectUri requerido");
    return;
  }

  // Construir URL de callback
  const callbackUrl = new URL(redirectUri);
  callbackUrl.searchParams.set("code", "mock-auth-code-" + Date.now());
  callbackUrl.searchParams.set("state", state || "");

  // Página HTML mínima con auto-redirect (o botón manual)
  res.send(`<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>SIGED Mock OAuth</title>
  <style>
    body { font-family: system-ui; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f0f2f5; }
    .card { background: white; padding: 2rem 3rem; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
    h2 { color: #1a365d; margin-bottom: 0.5rem; }
    p { color: #666; margin-bottom: 1.5rem; }
    .user { background: #f7fafc; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; text-align: left; font-size: 0.9rem; }
    .user strong { color: #2d3748; }
    button { background: #2b6cb0; color: white; border: none; padding: 0.75rem 2rem; border-radius: 8px; font-size: 1rem; cursor: pointer; }
    button:hover { background: #2c5282; }
    .auto { color: #999; font-size: 0.8rem; margin-top: 1rem; }
  </style>
</head>
<body>
  <div class="card">
    <h2>Mock OAuth Login</h2>
    <p>Entorno de desarrollo — AppID: <code>${appId || "?"}</code></p>
    <div class="user">
      <strong>Usuario:</strong> ${MOCK_USER.name}<br>
      <strong>Email:</strong> ${MOCK_USER.email}<br>
      <strong>OpenID:</strong> ${MOCK_USER.openId}
    </div>
    <a href="${callbackUrl.toString()}"><button>Iniciar sesion como Dev</button></a>
    <p class="auto">Redireccion automatica en 3 segundos...</p>
  </div>
  <script>
    setTimeout(() => { window.location.href = "${callbackUrl.toString()}"; }, 3000);
  </script>
</body>
</html>`);
});

// ─── POST /ExchangeToken ────────────────────────────────────
app.post("/webdev.v1.WebDevAuthPublicService/ExchangeToken", (req, res) => {
  console.log("[MockOAuth] ExchangeToken request:", req.body);

  res.json({
    accessToken: "mock-access-token-" + Date.now(),
    tokenType: "Bearer",
    expiresIn: 86400,
    refreshToken: "mock-refresh-token-" + Date.now(),
    scope: "openid profile email",
    idToken: "mock-id-token",
  });
});

// ─── POST /GetUserInfo ──────────────────────────────────────
app.post("/webdev.v1.WebDevAuthPublicService/GetUserInfo", (req, res) => {
  console.log("[MockOAuth] GetUserInfo request:", req.body);
  res.json(MOCK_USER);
});

// ─── POST /GetUserInfoWithJwt ───────────────────────────────
app.post("/webdev.v1.WebDevAuthPublicService/GetUserInfoWithJwt", (req, res) => {
  console.log("[MockOAuth] GetUserInfoWithJwt request:", req.body);
  res.json(MOCK_USER);
});

// ─── Start ──────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n========================================`);
  console.log(`  Mock OAuth Server corriendo en:`);
  console.log(`  http://localhost:${PORT}`);
  console.log(`========================================`);
  console.log(`  Login page:    http://localhost:${PORT}/app-auth`);
  console.log(`  ExchangeToken: POST http://localhost:${PORT}/webdev.v1.WebDevAuthPublicService/ExchangeToken`);
  console.log(`  GetUserInfo:   POST http://localhost:${PORT}/webdev.v1.WebDevAuthPublicService/GetUserInfo`);
  console.log(`========================================\n`);
});
