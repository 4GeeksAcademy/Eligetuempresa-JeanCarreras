const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const acorn = require("acorn");
const { JSDOM } = require("jsdom");
const createDOMPurify = require("dompurify");

const root = path.resolve(__dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const helper = read("uis/security.js");
const results = {};
const purifierBytes = fs.readFileSync(require.resolve("dompurify").replace(/purify\.cjs\.js$/, "purify.min.js"));
const integrity = "sha384-" + crypto.createHash("sha384").update(purifierBytes).digest("base64");

function prepare(html, url) {
  const dom = new JSDOM(html, { url, runScripts: "outside-only" });
  dom.window.Headers = Headers;
  dom.window.DOMPurify = createDOMPurify(dom.window);
  dom.window.setInterval = () => 0;
  dom.window.eval(helper);
  return dom;
}

const session = prepare("", "https://brasaland.example");
session.window.localStorage.setItem("brasaland_token", "isolated-session");
const security = session.window.BrasalandSecurity;
assert.equal(security.authHeaders("https://brasaland.example").authorization, "Bearer isolated-session");
session.window.localStorage.setItem("brasaland_access_token", "next-session");
assert.equal(security.authHeaders("https://brasaland.example").authorization, "Bearer next-session");
assert.throws(() => security.authHeaders("https://attacker.invalid"));
assert.throws(() => security.authHeaders("http://brasaland.example"));
assert.equal(security.authHeaders("https://brasaland.example", { "X-API-Token": "public" })["x-api-token"], undefined);
assert.equal(security.sanitizeHTML('<div style="height:75%;"></div>'), '<div style="height:75%;"></div>');
assert(!security.sanitizeHTML('<div style="background:url(https://attacker.invalid)"></div>').includes("style"));
results.credentials = "session bearer; untrusted destinations and legacy headers rejected";
session.window.close();

for (const directory of ["executive-dashboard", "marketing-loyalty-app"]) {
  const html = read(`uis/${directory}/index.html`);
  assert(html.includes(integrity), "DOMPurify integrity does not match installed version");
  const source = read(`uis/${directory}/app.js`);
  const ast = acorn.parse(source, { ecmaVersion: "latest" });
  let sinks = 0;
  function inspect(node) {
    if (!node || typeof node !== "object") return;
    if (node.type === "AssignmentExpression" && node.left.type === "MemberExpression" && node.left.property.name === "innerHTML") {
      assert.equal(node.right.type, "CallExpression");
      assert.equal(node.right.callee.property.name, "sanitizeHTML");
      sinks += 1;
    }
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) value.forEach(inspect);
      else if (value && typeof value === "object") inspect(value);
    }
  }
  inspect(ast);
  assert(!/brasaland-(executive|operations)-token/.test(source));
  const dom = prepare(html, "file:///audit/index.html");
  dom.window.eval(source);
  let rendered;
  if (directory === "executive-dashboard") {
    dom.window.renderHrRequests([{
      employee_name: "Audit", market: "CO", start_date: "2026-01-01", end_date: "2026-01-02",
      status: "pending", request_type: "leave", total_days: 1, id: 1,
      reason: '<img src=x onerror="window.compromised=true"><script>bad()</script>',
    }]);
    rendered = dom.window.document.getElementById("hrRequestsRows").innerHTML;
    assert(rendered.includes("Audit"));
  } else {
    dom.window.renderRecommendations([{
      name: "<img src=x onerror=alert(1)>", reason: "<script>bad()</script>", score: 1, expected_price: 10,
    }], "USD");
    rendered = dom.window.document.getElementById("recommendationsRows").innerHTML;
  }
  assert(!/onerror|<script/.test(rendered));
  results[directory] = { protected_html_sinks: sinks, xss_payload: "filtered", sri: "matches" };
  dom.window.close();
}
console.log(JSON.stringify(results, null, 2));