#!/usr/bin/env python3
"""Coleta horária dos quantitativos de solicitações RSC (UFPB) e regera o dashboard HTML.

Fonte oficial: https://rsctae.ufpb.br/portal (API pública: api.ufpb.br/rsc/publico/solicitacoes/alfabeticas)
"""
import csv
import html
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
HISTORY_CSV = DOCS_DIR / "rsc_history.csv"
DASHBOARD_HTML = DOCS_DIR / "index.html"

API_BASE = "https://api.ufpb.br/rsc/publico/solicitacoes/alfabeticas?page=0&size=1"

STATUS_CODES = {
    "aguardando_relator": "SUBMETIDA",
    "analise_memorial": "EM_ANALISE",
    "analise_criterios": "EM_ANALISE_CRITERIOS",
    "em_votacao": "EM_VOTACAO",
    "aguardando_homologacao": "APROVADO",
    "indeferido": "INDEFERIDO",
    "homologado": "HOMOLOGADA",
}

FIELDNAMES = [
    "timestamp",
    "total",
    "aguardando_relator",
    "relator_designado",
    "analise_memorial",
    "analise_criterios",
    "em_votacao",
    "aguardando_homologacao",
    "indeferido",
    "homologado",
]

TZ_BR = timezone(timedelta(hours=-3))
MAX_HISTORY_POINTS = 500


def fetch_count(url: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "rsc-tae-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["page"]["totalElements"]


def collect_snapshot() -> dict:
    total = fetch_count(API_BASE)
    counts = {}
    for key, code in STATUS_CODES.items():
        counts[key] = fetch_count(f"{API_BASE}&status={code}")

    row = {
        "timestamp": datetime.now(TZ_BR).isoformat(timespec="seconds"),
        "total": total,
        "aguardando_relator": counts["aguardando_relator"],
        "relator_designado": total - counts["aguardando_relator"],
        "analise_memorial": counts["analise_memorial"],
        "analise_criterios": counts["analise_criterios"],
        "em_votacao": counts["em_votacao"],
        "aguardando_homologacao": counts["aguardando_homologacao"],
        "indeferido": counts["indeferido"],
        "homologado": counts["homologado"],
    }
    return row


def append_history(row: dict) -> list:
    file_exists = HISTORY_CSV.exists()
    with open(HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    with open(HISTORY_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        history = list(reader)
    return history


def build_html(history: list) -> str:
    latest = history[-1]

    def as_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    dt = datetime.fromisoformat(latest["timestamp"])
    data_fmt = dt.strftime("%d/%m/%Y")
    hora_fmt = dt.strftime("%H:%M")

    cards = [
        ("Total de solicitações", latest["total"], "total"),
        ("Aguardando relator", latest["aguardando_relator"], "aguardando"),
        ("Com relator designado", latest["relator_designado"], "relator"),
        ("Análise do memorial", latest["analise_memorial"], "memorial"),
        ("Análise de critérios", latest["analise_criterios"], "criterios"),
        ("Em votação", latest["em_votacao"], "votacao"),
        ("Aguardando homologação", latest["aguardando_homologacao"], "homolog-aguard"),
        ("Indeferidas", latest["indeferido"], "indeferido"),
        ("Homologadas", latest["homologado"], "homologado"),
    ]

    cards_html = "\n".join(
        f'''      <div class="card card-{cls}">
        <span class="card-label">{html.escape(label)}</span>
        <span class="card-value">{as_int(value)}</span>
      </div>'''
        for label, value, cls in cards
    )

    # Mantém a página em tamanho razoável (~20 dias de coleta horária).
    capped_history = history[-MAX_HISTORY_POINTS:]
    history_rows = [
        {
            "t": row["timestamp"],
            "total": as_int(row["total"]),
            "aguardando_relator": as_int(row["aguardando_relator"]),
            "relator_designado": as_int(row["relator_designado"]),
            "analise_memorial": as_int(row["analise_memorial"]),
            "analise_criterios": as_int(row["analise_criterios"]),
            "em_votacao": as_int(row["em_votacao"]),
            "aguardando_homologacao": as_int(row["aguardando_homologacao"]),
            "indeferido": as_int(row["indeferido"]),
            "homologado": as_int(row["homologado"]),
        }
        for row in capped_history
    ]
    payload = {"generated_at": latest["timestamp"], "history": history_rows}
    payload_json = json.dumps(payload, ensure_ascii=False, indent=None)

    template = HTML_TEMPLATE
    template = template.replace("__DATA_FMT__", data_fmt)
    template = template.replace("__HORA_FMT__", hora_fmt)
    template = template.replace("__CARDS_HTML__", cards_html)
    template = template.replace("__RAW_DATA_JSON__", payload_json)
    template = template.replace("__TOTAL_REGISTROS__", str(len(history)))
    return template


HTML_TEMPLATE = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Monitor RSC-TAE UFPB</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f4f6f9;
    --card-bg: #ffffff;
    --text: #1a1f29;
    --muted: #5b6472;
    --border: #e2e6ec;
    --accent: #1e5fbf;
    --accent-2: #2f9e6b;
    --shadow: 0 1px 3px rgba(20,25,35,0.08), 0 1px 2px rgba(20,25,35,0.06);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #12151b;
      --card-bg: #1b1f28;
      --text: #eef1f6;
      --muted: #9aa4b2;
      --border: #2a2f3a;
      --accent: #6ea8ff;
      --accent-2: #4fd497;
      --shadow: 0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
    }
  }
  :root[data-theme="dark"] {
    --bg: #12151b; --card-bg: #1b1f28; --text: #eef1f6; --muted: #9aa4b2;
    --border: #2a2f3a; --accent: #6ea8ff; --accent-2: #4fd497;
    --shadow: 0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
  }
  :root[data-theme="light"] {
    --bg: #f4f6f9; --card-bg: #ffffff; --text: #1a1f29; --muted: #5b6472;
    --border: #e2e6ec; --accent: #1e5fbf; --accent-2: #2f9e6b;
    --shadow: 0 1px 3px rgba(20,25,35,0.08), 0 1px 2px rgba(20,25,35,0.06);
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    -webkit-text-size-adjust: 100%;
    overflow-x: hidden;
  }
  .wrap {
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px 16px 48px;
  }
  header {
    margin-bottom: 20px;
  }
  h1 {
    font-size: 1.35rem;
    margin: 0 0 4px;
    line-height: 1.3;
  }
  .subtitle {
    color: var(--muted);
    font-size: 0.9rem;
    margin: 0 0 2px;
  }
  .timestamp {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 10px;
    padding: 8px 14px;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 999px;
    font-size: 0.9rem;
    box-shadow: var(--shadow);
  }
  .timestamp b { color: var(--accent); }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin: 20px 0 28px;
  }
  .card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 16px;
    box-shadow: var(--shadow);
    display: flex;
    flex-direction: column;
    gap: 6px;
    border-left: 4px solid var(--accent);
  }
  .card-label {
    font-size: 0.78rem;
    color: var(--muted);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.02em;
  }
  .card-value {
    font-size: 1.9rem;
    font-weight: 700;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }
  .card-total { border-left-color: var(--accent); grid-column: span 1; }
  .card-homologado { border-left-color: var(--accent-2); }
  .card-homologado .card-value { color: var(--accent-2); }
  .card-indeferido { border-left-color: #d3564a; }
  .card-indeferido .card-value { color: #d3564a; }
  section.panel {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
  }
  section.panel h2 {
    font-size: 1rem;
    margin: 0 0 12px;
  }
  #chart-wrap {
    width: 100%;
    overflow-x: auto;
  }
  svg#chart {
    width: 100%;
    height: auto;
    display: block;
  }
  .axis-label { fill: var(--muted); font-size: 10px; }
  .grid-line { stroke: var(--border); stroke-width: 1; }
  .chart-line { fill: none; stroke: var(--accent-2); stroke-width: 2.5; }
  .chart-area { fill: var(--accent-2); opacity: 0.12; }
  .chart-dot { fill: var(--accent-2); }
  .chart-empty { fill: var(--muted); font-size: 13px; }
  footer {
    color: var(--muted);
    font-size: 0.78rem;
    text-align: center;
    margin-top: 24px;
  }
  footer a { color: var(--accent); }
  .badge {
    display: inline-block;
    font-size: 0.72rem;
    color: var(--muted);
    margin-left: 8px;
  }
  .notice {
    text-align: left;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
    margin-top: 24px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .notice p {
    margin: 0;
    font-size: 0.78rem;
    line-height: 1.5;
    color: var(--muted);
  }
  .notice p strong {
    color: var(--text);
  }
  .notice a { color: var(--accent); }
  details.raw-data {
    margin-top: 18px;
    color: var(--muted);
    font-size: 0.78rem;
  }
  details.raw-data summary {
    cursor: pointer;
    user-select: none;
  }
  details.raw-data pre {
    margin: 8px 0 0;
    padding: 10px;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow-x: auto;
    font-size: 0.68rem;
    line-height: 1.4;
    white-space: pre-wrap;
    word-break: break-word;
  }
  @media (max-width: 480px) {
    h1 { font-size: 1.15rem; }
    .card-value { font-size: 1.6rem; }
  }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Monitor de Solicitações RSC — UFPB</h1>
    <p class="subtitle">Acompanhamento horário do andamento das solicitações de RSC/TAE em tramitação, com base na consulta pública oficial.</p>
    <div class="timestamp">📅 Atualizado em <b>__DATA_FMT__</b> às <b>__HORA_FMT__</b> (horário de Brasília)</div>
  </header>

  <div class="grid">
__CARDS_HTML__
  </div>

  <section class="panel">
    <h2>Solicitações homologadas ao longo do tempo <span class="badge">__TOTAL_REGISTROS__ registro(s)</span></h2>
    <div id="chart-wrap">
      <svg id="chart" viewBox="0 0 800 300" preserveAspectRatio="xMidYMid meet"></svg>
    </div>
  </section>

  <footer>
    <div class="notice">
      <p>🕐 <strong>Janela de atualização:</strong> os dados são coletados automaticamente de hora em hora, apenas de segunda a sexta-feira, das 7h às 20h (horário de Brasília). Fora desse intervalo e aos finais de semana, este painel permanece parado, exibindo os números da última coleta.</p>
      <p>⚠️ <strong>Aviso:</strong> este é um painel de acompanhamento independente e não oficial, sem qualquer responsabilidade sobre a exatidão ou atualidade dos dados aqui exibidos. A fonte oficial e sempre atual é a Consulta Pública do RSC-TAE/UFPB, disponível em <a href="https://rsctae.ufpb.br/portal" target="_blank" rel="noopener">rsctae.ufpb.br/portal</a> — em caso de dúvida ou divergência, ela prevalece.</p>
    </div>
    <details class="raw-data">
      <summary>Dados históricos (JSON, uso interno da coleta automática)</summary>
      <pre id="rsc-raw-data">__RAW_DATA_JSON__</pre>
    </details>
  </footer>
</div>

<script>
  var payload = JSON.parse(document.getElementById('rsc-raw-data').textContent);
  var historyData = payload.history || [];
  var chartData = historyData.map(function(d) { return {t: d.t, v: d.homologado}; });

  function renderChart() {
    var svg = document.getElementById('chart');
    var W = 800, H = 300;
    var padL = 40, padR = 16, padT = 16, padB = 34;
    svg.innerHTML = '';

    if (!chartData || chartData.length === 0) {
      var t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      t.setAttribute('x', W/2); t.setAttribute('y', H/2);
      t.setAttribute('text-anchor', 'middle');
      t.setAttribute('class', 'chart-empty');
      t.textContent = 'Ainda não há histórico suficiente. Volte em algumas horas.';
      svg.appendChild(t);
      return;
    }

    var values = chartData.map(function(d){ return d.v; });
    var maxV = Math.max.apply(null, values);
    var minV = 0;
    var range = Math.max(maxV - minV, 1);
    var n = chartData.length;

    var plotW = W - padL - padR;
    var plotH = H - padT - padB;

    function x(i) { return n === 1 ? padL + plotW/2 : padL + (plotW * i) / (n - 1); }
    function y(v) { return padT + plotH - ((v - minV) / range) * plotH; }

    var ns = 'http://www.w3.org/2000/svg';

    var gridCount = 4;
    for (var g = 0; g <= gridCount; g++) {
      var gv = Math.round((range * g) / gridCount);
      var gy = y(gv);
      var line = document.createElementNS(ns, 'line');
      line.setAttribute('x1', padL); line.setAttribute('x2', W - padR);
      line.setAttribute('y1', gy); line.setAttribute('y2', gy);
      line.setAttribute('class', 'grid-line');
      svg.appendChild(line);

      var label = document.createElementNS(ns, 'text');
      label.setAttribute('x', padL - 8); label.setAttribute('y', gy + 3);
      label.setAttribute('text-anchor', 'end');
      label.setAttribute('class', 'axis-label');
      label.textContent = gv;
      svg.appendChild(label);
    }

    var pathD = '';
    var areaD = '';
    chartData.forEach(function(d, i) {
      var px = x(i), py = y(d.v);
      pathD += (i === 0 ? 'M' : 'L') + px + ',' + py + ' ';
    });
    areaD = pathD + 'L' + x(n-1) + ',' + y(minV) + ' L' + x(0) + ',' + y(minV) + ' Z';

    var area = document.createElementNS(ns, 'path');
    area.setAttribute('d', areaD);
    area.setAttribute('class', 'chart-area');
    svg.appendChild(area);

    var path = document.createElementNS(ns, 'path');
    path.setAttribute('d', pathD.trim());
    path.setAttribute('class', 'chart-line');
    svg.appendChild(path);

    var labelEvery = Math.max(1, Math.ceil(n / 6));
    chartData.forEach(function(d, i) {
      var px = x(i), py = y(d.v);
      var dot = document.createElementNS(ns, 'circle');
      dot.setAttribute('cx', px); dot.setAttribute('cy', py);
      dot.setAttribute('r', 3);
      dot.setAttribute('class', 'chart-dot');
      var titleEl = document.createElementNS(ns, 'title');
      var dt = new Date(d.t);
      titleEl.textContent = dt.toLocaleString('pt-BR') + ' — ' + d.v + ' homologada(s)';
      dot.appendChild(titleEl);
      svg.appendChild(dot);

      if (i % labelEvery === 0 || i === n - 1) {
        var lbl = document.createElementNS(ns, 'text');
        lbl.setAttribute('x', px); lbl.setAttribute('y', H - padB + 16);
        lbl.setAttribute('text-anchor', 'middle');
        lbl.setAttribute('class', 'axis-label');
        var dt2 = new Date(d.t);
        lbl.textContent = dt2.toLocaleDateString('pt-BR', {day:'2-digit', month:'2-digit'}) + ' ' + dt2.toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'});
        svg.appendChild(lbl);
      }
    });
  }

  renderChart();
  window.addEventListener('resize', renderChart);
</script>
</body>
</html>
"""


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    row = collect_snapshot()
    history = append_history(row)
    html_out = build_html(history)
    DASHBOARD_HTML.write_text(html_out, encoding="utf-8")
    print(f"OK: snapshot registrado ({row['timestamp']}). Total={row['total']} Homologadas={row['homologado']}")
    print(f"Histórico: {HISTORY_CSV} ({len(history)} registros)")
    print(f"Dashboard: {DASHBOARD_HTML}")


if __name__ == "__main__":
    main()
