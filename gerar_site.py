"""
Site do setup em formato de PERCURSO: a pessoa rola e as pecas
passam de lado, uma de cada vez.

  MODELO     le o JSON, prepara as fotos
  VISAO      monta HTML e CSS
  CONTROLE   grava os arquivos
"""
import base64
import html
import io
import json
import pathlib
import re
import shutil

import numpy as np
from PIL import Image

ENTRADA = pathlib.Path("/mnt/user-data/uploads/setup-inventory-2026-10-02.json")
LOGO = pathlib.Path("/mnt/user-data/outputs/logo.png")
SAIDA = pathlib.Path("/mnt/user-data/outputs/setup-site")
IMG = SAIDA / "img"

FUNDO_FOTO = (246, 247, 249)
LADO_FOTO = 760
OCUPACAO = 0.84

# nome no JSON -> (secao, nome exibido, marca, o que faz)
CURADORIA = {
    "Processador AMD Ryzen 7 9700X":
        ("PC", "Ryzen 7 9700X", "AMD", "Processa o jogo e a transmissão ao mesmo tempo."),
    "Placa de Video MSI GeForce RTX 5070":
        ("PC", "GeForce RTX 5070", "MSI", "Desenha o jogo e codifica o vídeo da live."),
    "PLACA MAE GIGABYTE B850 GAMING WIFI 6":
        ("PC", "B850 Gaming WiFi 6", "Gigabyte", "Onde todas as peças se encontram."),
    "Memoria DDR5 Corsair Vengeance RGB, 16GB, 5600MHz":
        ("PC", "Vengeance RGB 16GB", "Corsair", "Memória DDR5 a 5600 MHz."),
    "SSD Kingston NV3, 1TB, M.2 NVMe":
        ("PC", "NV3 1TB", "Kingston", "Guarda os jogos e as gravações das lives."),
    "FONTE MSI MAG A750GL 750W 80 PLUS":
        ("PC", "MAG A750GL", "MSI", "Fonte de 750 W com selo 80 Plus."),
    "Water Cooler MSI MAG Coreliquid A12, 360mm":
        ("PC", "MAG Coreliquid A12", "MSI", "Water cooler de 360 mm no processador."),
    "Kit 6 Fans Coolers Argb Rgb 120mm":
        ("PC", "Seis fans ARGB", "", "Tiram o calor de dentro do gabinete."),
    "Placa de Captura":
        ("PC", "Placa de captura", "", "Leva a imagem e o som do PS5 para o PC."),

    "Teclado Mecânico Gamer SuperFrame Phantom":
        ("Periféricos", "Phantom", "SuperFrame", "Teclado mecânico."),
    "Mouse Gamer X11 Attack Shark":
        ("Periféricos", "X11", "Attack Shark", "Mouse."),
    "FIFINE Kit de Microfone - AM8PROT":
        ("Periféricos", "AM8PROT", "FIFINE", "O microfone que você ouve na live."),
    "FIFINE SC8":
        ("Periféricos", "SC8", "FIFINE", "Mesa de som: junta PS5, PC e microfone num fone só."),
    "TRN Conch Earphone Lucky Bag":
        ("Periféricos", "Conch", "TRN", "Fone intra que eu uso jogando."),
    "Headset Gamer Redragon Zeus X":
        ("Periféricos", "Zeus X", "Redragon", "Headset de reserva."),

    "Monitor Gamer Aoc 24 180hz":
        ("Monitores", "AOC 24 polegadas", "AOC", "Monitor principal, 180 Hz."),
    "AOC Speed 24G2HE5":
        ("Monitores", "Speed 24G2HE5", "AOC", "Monitor de apoio, onde fica o chat."),
    "Suporte De Mesa Para Tv/monitor De 17 Até 30 Preto Nb F80":
        ("Monitores", "Braço NB F80", "", "Tira os monitores da mesa e libera espaço."),

    "PlayStation 5 Slim":
        ("Console", "PlayStation 5 Slim", "Sony", "Onde rodam o R6 e o EA FC."),
    "Controle Sony DualSense PS5, Sem Fio , Galactic Purple":
        ("Console", "DualSense Galactic Purple", "Sony", "Controle."),
    "Base de Carregamento Sony Para Controle DualSense":
        ("Console", "Base de carregamento", "Sony", "Deixa os controles sempre prontos."),
    "Hub Usb 4 Portas Para Ps5 Playstation 5 Slim":
        ("Console", "Hub USB de quatro portas", "", "Mais portas na frente do PS5."),

    "Cadeira De Escritório Ergonômica Mônaco Bt07 Luvinco":
        ("Estação", "Mônaco BT07", "Luvinco", "Cadeira, para aguentar live longa."),
    "Mesa para Escritório em L":
        ("Estação", "Mesa em L", "", "Cabe o PC, os dois monitores e o PS5."),
}

SECOES = ["PC", "Periféricos", "Monitores", "Console", "Estação"]
CORES = {
    "PC":          "#efa02a",
    "Periféricos": "#9bd45f",
    "Monitores":   "#55c8e8",
    "Console":     "#a981f0",
    "Estação":     "#8e99ab",
}


# ===========================================================
#  MODELO
# ===========================================================
def slug(texto):
    texto = re.sub(r"[^a-z0-9]+", "-", texto.lower().strip())
    return re.sub(r"-+", "-", texto).strip("-")


def _aparar(im, tolerancia=16):
    a = np.array(im.convert("RGB")).astype(int)
    moldura = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    cor = np.median(moldura, axis=0)
    if cor.min() < 200:
        return im
    vazio = np.abs(a - cor).max(axis=2) < tolerancia
    linhas = np.where(~vazio.all(axis=1))[0]
    colunas = np.where(~vazio.all(axis=0))[0]
    if len(linhas) == 0 or len(colunas) == 0:
        return im
    f = 6
    return im.crop((max(colunas[0] - f, 0), max(linhas[0] - f, 0),
                    min(colunas[-1] + f, im.width), min(linhas[-1] + f, im.height)))


def preparar_foto(dados):
    im = Image.open(io.BytesIO(dados)).convert("RGB")
    im.thumbnail((1100, 1100), Image.LANCZOS)
    im = _aparar(im)
    alvo = int(LADO_FOTO * OCUPACAO)
    im.thumbnail((alvo, alvo), Image.LANCZOS)
    tela = Image.new("RGB", (LADO_FOTO, LADO_FOTO), FUNDO_FOTO)
    tela.paste(im, ((LADO_FOTO - im.width) // 2, (LADO_FOTO - im.height) // 2))
    saida = io.BytesIO()
    tela.save(saida, "JPEG", quality=86, optimize=True)
    return saida.getvalue()


def carregar():
    IMG.mkdir(parents=True, exist_ok=True)
    for f in IMG.glob("*"):
        f.unlink()

    dados = json.loads(ENTRADA.read_text(encoding="utf-8"))
    vistos = {}
    for item in dados["items"]:
        if item.get("status") != "owned":
            continue
        bruto = item["name"].strip()
        if bruto in vistos:
            vistos[bruto]["qtd"] += 1
            continue
        if bruto not in CURADORIA:
            print("  sem curadoria:", bruto)
            continue
        secao, nome, marca, papel = CURADORIA[bruto]
        arquivo = ""
        url = item.get("imageUrl") or ""
        if url.startswith("data:image/"):
            arquivo = f"{slug(nome)}.jpg"
            (IMG / arquivo).write_bytes(preparar_foto(base64.b64decode(url.split(",", 1)[1])))
        vistos[bruto] = dict(secao=secao, nome=nome, marca=marca,
                             papel=papel, img=arquivo, qtd=1)

    ordem = {s: i for i, s in enumerate(SECOES)}
    pecas = sorted(vistos.values(), key=lambda p: ordem[p["secao"]])
    return pecas


# ===========================================================
#  VISAO
# ===========================================================
CSS = """
:root {
  --fundo:  #060a10;
  --tinta:  #f3f0e8;
  --fraco:  #8a95a6;
  --claro:  #f6f7f9;
  --linha:  rgba(255,255,255,.1);
  --ouro:   #efa02a;
  --verde:  #9bd45f;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: auto; }

body {
  background: var(--fundo);
  color: var(--tinta);
  font-family: "Space Grotesk", system-ui, sans-serif;
  overflow-x: hidden;
}

h1, h2, .nome, .contador, .canal {
  font-family: "Chakra Petch", system-ui, sans-serif;
  font-weight: 600;
}

/* ---------- abertura ---------- */
.abertura {
  height: 100vh;
  display: grid;
  place-items: center;
  text-align: center;
  padding: 24px;
  position: relative;
}

.abertura img {
  width: 132px;
  filter: drop-shadow(0 10px 30px rgba(239,160,42,.3));
  animation: flutua 5s ease-in-out infinite;
}

@keyframes flutua {
  0%, 100% { transform: translateY(0) rotate(-1deg); }
  50%      { transform: translateY(-9px) rotate(1deg); }
}

.abertura h1 {
  margin-top: 18px;
  font-size: clamp(38px, 7vw, 76px);
  letter-spacing: -2px;
  line-height: .95;
}
.abertura h1 .c { color: var(--ouro); }
.abertura h1 .s { color: var(--verde); }

.abertura p {
  margin-top: 14px;
  color: var(--fraco);
  font-size: 17px;
  max-width: 34ch;
}

.rolar {
  position: absolute;
  bottom: 34px; left: 50%;
  transform: translateX(-50%);
  color: var(--fraco);
  font-size: 13px;
  letter-spacing: .14em;
}
.rolar i {
  display: block;
  width: 1px; height: 30px;
  margin: 10px auto 0;
  background: linear-gradient(var(--fraco), transparent);
  animation: desce 1.8s ease-in-out infinite;
}
@keyframes desce {
  0%   { transform: scaleY(0); transform-origin: top; }
  50%  { transform: scaleY(1); transform-origin: top; }
  100% { transform: scaleY(0); transform-origin: bottom; }
}

/* ---------- o percurso ---------- */
.trilho { position: relative; }

.palco {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  width: max-content;
  will-change: transform;
}

.cena {
  width: 100vw;
  height: 100vh;
  flex: none;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  gap: 60px;
  padding: 0 clamp(28px, 7vw, 120px);
  position: relative;
  overflow: hidden;
}

.cena.espelhada .foto  { order: 2; }
.cena.espelhada .texto { order: 1; }

/* a categoria passa ao fundo, mais devagar que a peca */
.marcador {
  position: absolute;
  left: 0; bottom: 6vh;
  font-family: "Chakra Petch", sans-serif;
  font-weight: 700;
  font-size: clamp(90px, 17vw, 230px);
  line-height: .8;
  letter-spacing: -.04em;
  color: var(--cor);
  opacity: .07;
  white-space: nowrap;
  pointer-events: none;
  will-change: transform;
}

.foto {
  justify-self: center;
  width: min(42vw, 50vh);
  aspect-ratio: 1;
  border-radius: 6px;
  overflow: hidden;
  background: var(--claro);
  box-shadow: 0 30px 70px -30px rgba(0,0,0,.9), 0 0 0 1px var(--linha);
  will-change: transform;
}
.foto img { width: 100%; height: 100%; object-fit: cover; display: block; }

.texto { max-width: 46ch; will-change: transform; }

.marca {
  color: var(--cor);
  font-size: 14px;
  letter-spacing: .14em;
  min-height: 20px;
}

.nome {
  font-size: clamp(34px, 4.6vw, 62px);
  line-height: 1.02;
  letter-spacing: -1.4px;
  margin: 6px 0 14px;
}

.papel {
  color: var(--fraco);
  font-size: clamp(16px, 1.4vw, 20px);
  line-height: 1.45;
}

.extra {
  margin-top: 22px;
  padding-top: 14px;
  border-top: 1px solid var(--linha);
  color: var(--fraco);
  font-size: 14px;
}
.extra b { color: var(--cor); font-weight: 500; }

/* ---------- barra de progresso ---------- */
.progresso {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  height: 54px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 clamp(20px, 5vw, 60px);
  background: linear-gradient(transparent, rgba(6,10,16,.92) 45%);
  pointer-events: none;
  opacity: 0;
  transition: opacity .3s;
  z-index: 5;
}
.progresso.ativa { opacity: 1; }

.barra {
  flex: 1;
  height: 2px;
  background: rgba(255,255,255,.12);
  position: relative;
}
.barra span {
  position: absolute;
  inset: 0 auto 0 0;
  background: var(--cor-atual, var(--ouro));
  transition: background .4s;
}
.contador {
  font-size: 14px;
  color: var(--fraco);
  font-variant-numeric: tabular-nums;
}
.contador b { color: var(--tinta); font-weight: 600; }

/* ---------- fim ---------- */
.fim {
  min-height: 100vh;
  display: grid;
  place-items: center;
  text-align: center;
  padding: 80px 24px;
}
.fim h2 { font-size: clamp(28px, 4vw, 48px); letter-spacing: -1px; }
.fim p { margin-top: 12px; color: var(--fraco); }

.canais {
  margin-top: 30px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}
.canal {
  font-size: 19px;
  text-decoration: none;
  padding: 14px 26px;
  border-radius: 6px;
  transition: transform .12s, filter .12s;
}
.canal:hover, .canal:focus-visible { transform: translateY(-2px); filter: brightness(1.08); }
.canal.twitch { background: #9146ff; color: #fff; }
.canal.kick   { color: var(--verde); box-shadow: inset 0 0 0 2px var(--verde); }

.secundario {
  display: inline-block;
  margin-top: 20px;
  color: var(--fraco);
  font-size: 15px;
  text-decoration: none;
  border-bottom: 1px solid var(--linha);
}
.secundario:hover, .secundario:focus-visible { color: var(--tinta); }

.nota { margin-top: 26px; color: var(--fraco); font-size: 13px; }

/* ---------- celular: vira sequencia vertical ---------- */
@media (max-width: 900px) {
  .palco { position: static; width: auto; flex-direction: column; transform: none !important; }
  .trilho { height: auto !important; }
  .cena {
    width: 100%;
    height: auto;
    min-height: 92vh;
    grid-template-columns: 1fr;
    gap: 26px;
    padding: 70px 22px;
    align-content: center;
  }
  .cena.espelhada .foto, .cena.espelhada .texto { order: initial; }
  .foto { width: min(76vw, 42vh); }
  .marcador { font-size: 74px; bottom: 2vh; opacity: .06; transform: none !important; }
  .progresso { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .palco { position: static; width: auto; flex-direction: column; transform: none !important; }
  .trilho { height: auto !important; }
  .cena { width: 100%; height: auto; min-height: 90vh; }
  .abertura img, .rolar i { animation: none; }
  .marcador, .foto, .texto { transform: none !important; }
}
"""


def montar_html(pecas):
    e = html.escape
    cenas = []
    for i, p in enumerate(pecas):
        cor = CORES[p["secao"]]
        qtd = f' · <b>{p["qtd"]} unidades</b>' if p["qtd"] > 1 else ""
        foto = (f'<img src="img/{p["img"]}" alt="{e(p["nome"])}" loading="lazy">'
                if p["img"] else "")
        cenas.append(f"""      <section class="cena{' espelhada' if i % 2 else ''}"
               style="--cor:{cor}" data-cor="{cor}" data-secao="{e(p['secao'])}">
        <div class="marcador" aria-hidden="true">{e(p['secao'])}</div>
        <div class="foto">{foto}</div>
        <div class="texto">
          <div class="marca">{e(p['marca'])}</div>
          <h2 class="nome">{e(p['nome'])}</h2>
          <p class="papel">{e(p['papel'])}</p>
          <div class="extra">{e(p['secao'])}{qtd}</div>
        </div>
      </section>""")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bancada · thecoinsquash</title>
<meta name="description" content="Atravesse a bancada do thecoinsquash, peça por peça.">
<link rel="icon" href="img/logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=Space+Grotesk:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="estilo.css">
</head>
<body>

<header class="abertura">
  <div>
    <img src="img/logo.png" alt="" width="132" height="132">
    <h1>the<span class="c">coin</span><span class="s">squash</span></h1>
    <p>A bancada inteira, peça por peça. São {len(pecas)}, e todas trabalham quando a live começa.</p>
  </div>
  <div class="rolar">role para atravessar<i></i></div>
</header>

<main class="trilho" id="trilho">
  <div class="palco" id="palco">
{chr(10).join(cenas)}
  </div>
</main>

<div class="progresso" id="progresso" aria-hidden="true">
  <div class="barra"><span id="preenche" style="width:0%"></span></div>
  <div class="contador"><b id="atual">1</b> / {len(pecas)}</div>
</div>

<footer class="fim">
  <div>
    <h2>Chegou ao fim da bancada.</h2>
    <p>O resto só acontece ao vivo.</p>
    <div class="canais">
      <a class="canal twitch" href="https://twitch.tv/thecoinsquash">Assistir na Twitch</a>
      <a class="canal kick" href="https://kick.com/thecoinsquash">Assistir na Kick</a>
    </div>
    <a class="secundario" href="https://x.com/thecoinsquash">@thecoinsquash no X</a>
    <p class="nota">Terça a sexta, 21h30 · Sábado e domingo, 16h</p>
  </div>
</footer>

<script>
(function () {{
  const trilho = document.getElementById("trilho");
  const palco  = document.getElementById("palco");
  const cenas  = [...palco.querySelectorAll(".cena")];
  const barra  = document.getElementById("preenche");
  const atual  = document.getElementById("atual");
  const painel = document.getElementById("progresso");

  const semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)");
  const estreito     = window.matchMedia("(max-width: 900px)");
  function horizontal() {{ return !semMovimento.matches && !estreito.matches; }}

  // posicao ALVO vem da rolagem; posicao MOSTRADA persegue ela com
  // atraso. E esse atraso que da a sensacao de deslizar em vez de
  // ser puxado a cada clique da roda.
  let alvo = 0, mostrada = 0, rodando = false;
  const PERSEGUE = 0.085;

  function medir() {{
    if (!horizontal()) {{
      trilho.style.height = "";
      palco.style.transform = "";
      return;
    }}
    trilho.style.height = (cenas.length * 100) + "vh";
    alvo = mostrada = progresso();
    desenhar();
    ligar();
  }}

  function progresso() {{
    const topo = trilho.offsetTop;
    const curso = trilho.offsetHeight - window.innerHeight;
    return Math.min(Math.max((window.scrollY - topo) / curso, 0), 1);
  }}

  function ligar() {{
    if (rodando) return;
    rodando = true;
    requestAnimationFrame(quadro);
  }}

  function quadro() {{
    const falta = alvo - mostrada;
    mostrada += falta * PERSEGUE;
    if (Math.abs(falta) < 0.00015) {{ mostrada = alvo; rodando = false; }}
    else requestAnimationFrame(quadro);
    desenhar();
  }}

  function desenhar() {{
    const p = mostrada;
    const topo = trilho.offsetTop;
    const curso = trilho.offsetHeight - window.innerHeight;
    const dentro = window.scrollY > topo - window.innerHeight * .4 &&
                   window.scrollY < topo + curso + window.innerHeight * .4;
    painel.classList.toggle("ativa", dentro);

    const i = Math.min(Math.round(p * (cenas.length - 1)), cenas.length - 1);
    atual.textContent = i + 1;
    barra.style.width = (p * 100).toFixed(2) + "%";
    document.documentElement.style.setProperty("--cor-atual", cenas[i].dataset.cor);

    if (!horizontal()) return;
    palco.style.transform = "translate3d(" + (-p * (cenas.length - 1) * 100) + "vw,0,0)";

    const passo = 1 / (cenas.length - 1);
    cenas.forEach((cena, j) => {{
      const d = (p - j * passo) / passo;    // -1 entrando, 0 no centro, 1 saindo
      if (Math.abs(d) > 1.6) return;
      const foto = cena.querySelector(".foto");
      const texto = cena.querySelector(".texto");
      const marcador = cena.querySelector(".marcador");
      const suave = d * (1 - Math.min(Math.abs(d), 1) * .25);   // freia na saida
      if (foto) {{
        foto.style.transform = "translate3d(" + (suave * 5) + "vw,0,0) scale(" + (1 - Math.abs(d) * .05) + ")";
        foto.style.opacity = Math.max(1 - Math.abs(d) * 1.7, 0);
      }}
      if (texto) {{
        texto.style.transform = "translate3d(" + (suave * -2.5) + "vw,0,0)";
        texto.style.opacity = Math.max(1 - Math.abs(d) * 1.9, 0);
      }}
      if (marcador) marcador.style.transform = "translate3d(" + (d * 20) + "vw,0,0)";
    }});
  }}

  // ---- encaixe com curva propria ----
  // A rolagem suave do navegador tem tempo imprevisivel e da tranco.
  // Aqui a animacao e nossa: desacelera no fim e assenta na peca.
  let animando = false;

  function irPara(indice) {{
    const topo = trilho.offsetTop;
    const curso = trilho.offsetHeight - window.innerHeight;
    const passo = curso / (cenas.length - 1);
    const destino = Math.round(topo + Math.min(Math.max(indice, 0), cenas.length - 1) * passo);
    const partida = window.scrollY;
    const distancia = destino - partida;
    if (Math.abs(distancia) < 2) return;

    const duracao = Math.min(260 + Math.abs(distancia) * .35, 620);
    const comeco = performance.now();
    animando = true;

    function passoAnim(agora) {{
      const t = Math.min((agora - comeco) / duracao, 1);
      const e = 1 - Math.pow(1 - t, 3);          // desacelera no fim
      window.scrollTo(0, partida + distancia * e);
      if (t < 1) requestAnimationFrame(passoAnim);
      else animando = false;
    }}
    requestAnimationFrame(passoAnim);
  }}

  let ocioso = null;
  function aoRolar() {{
    alvo = progresso();
    ligar();
    if (animando) return;
    window.clearTimeout(ocioso);
    ocioso = window.setTimeout(() => {{
      if (!horizontal()) return;
      const topo = trilho.offsetTop;
      const curso = trilho.offsetHeight - window.innerHeight;
      if (window.scrollY < topo || window.scrollY > topo + curso) return;
      irPara(Math.round(alvo * (cenas.length - 1)));
    }}, 140);
  }}

  window.addEventListener("scroll", aoRolar, {{ passive: true }});

  window.addEventListener("keydown", (ev) => {{
    if (!horizontal()) return;
    const mapa = {{ ArrowRight: 1, ArrowDown: 1, PageDown: 1, ArrowLeft: -1, ArrowUp: -1, PageUp: -1 }};
    const dir = mapa[ev.key];
    if (!dir) return;
    const topo = trilho.offsetTop;
    const curso = trilho.offsetHeight - window.innerHeight;
    if (window.scrollY < topo || window.scrollY > topo + curso) return;
    ev.preventDefault();
    irPara(Math.round(alvo * (cenas.length - 1)) + dir);
  }});

  window.addEventListener("resize", medir);
  semMovimento.addEventListener("change", medir);
  estreito.addEventListener("change", medir);
  medir();
}})();
</script>
</body>
</html>
"""


# ===========================================================
#  CONTROLE
# ===========================================================
def main():
    pecas = carregar()
    print("  peças:", len(pecas))
    shutil.copy(LOGO, IMG / "logo.png")
    (SAIDA / "index.html").write_text(montar_html(pecas), encoding="utf-8")
    (SAIDA / "estilo.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    print("  gravado em", SAIDA)


if __name__ == "__main__":
    main()
