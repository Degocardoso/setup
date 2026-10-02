"""
Gera o site do setup do thecoinsquash.

Organizado em tres camadas:
  MODELO     le o JSON, filtra o que foi comprado, extrai as imagens
  VISAO      monta o HTML e o CSS
  CONTROLE   junta tudo e grava os arquivos
"""
import base64
import html
import io
import json
import pathlib
import re
import shutil
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

ENTRADA = pathlib.Path("/mnt/user-data/uploads/setup-inventory-2026-10-02.json")
LOGO = pathlib.Path("/mnt/user-data/outputs/logo.png")
SAIDA = pathlib.Path("/mnt/user-data/outputs/setup-site")
IMG = SAIDA / "img"


# ===========================================================
#  MODELO
# ===========================================================

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

# cada secao tem sua cor, como raridade de item
CORES = {
    "PC":          "#efa02a",
    "Periféricos": "#9bd45f",
    "Monitores":   "#55c8e8",
    "Console":     "#a981f0",   # o roxo do DualSense
    "Estação":     "#8e99ab",
}


def tirar_fundo(dados_png, lado_max=760):
    """Fotos de loja vem com fundo branco, que vira um quadrado aceso
    sobre o fundo escuro do site. Esta funcao apaga SO o branco que
    encosta na borda da imagem, entao peca branca (o PS5, por exemplo)
    continua inteira."""
    im = Image.open(io.BytesIO(dados_png)).convert("RGBA")
    im.thumbnail((lado_max, lado_max), Image.LANCZOS)
    a = np.array(im)
    rgb = a[:, :, :3].astype(int)

    claro = rgb.min(axis=2) > 246                      # praticamente branco puro
    neutro = (rgb.max(axis=2) - rgb.min(axis=2)) < 10  # sem cor nenhuma
    fundo = claro & neutro

    alt, larg = fundo.shape
    visto = np.zeros_like(fundo, dtype=bool)
    fila = deque()
    for x in range(larg):
        for y in (0, alt - 1):
            if fundo[y, x] and not visto[y, x]:
                visto[y, x] = True; fila.append((y, x))
    for y in range(alt):
        for x in (0, larg - 1):
            if fundo[y, x] and not visto[y, x]:
                visto[y, x] = True; fila.append((y, x))

    while fila:                                        # espalha pela borda
        y, x = fila.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < alt and 0 <= nx < larg and fundo[ny, nx] and not visto[ny, nx]:
                visto[ny, nx] = True; fila.append((ny, nx))

    if visto.mean() < 0.04:        # imagem ja era recortada: nao mexe
        saida = io.BytesIO(); im.save(saida, "PNG"); return saida.getvalue()

    # peca branca (PS5, base do controle) encosta no fundo e seria comida
    # junto. Se sobrar pouca imagem, e sinal de que o recorte errou.
    sobrou = 1 - visto.mean()
    if sobrou < 0.08:
        saida = io.BytesIO(); im.save(saida, "PNG"); return saida.getvalue()

    alfa = Image.fromarray(np.where(visto, 0, a[:, :, 3]).astype(np.uint8))
    alfa = alfa.filter(ImageFilter.GaussianBlur(0.6))  # borda menos serrilhada
    im.putalpha(alfa)
    im = im.crop(im.getbbox() or (0, 0, larg, alt))
    saida = io.BytesIO(); im.save(saida, "PNG")
    return saida.getvalue()


def slug(texto):
    texto = re.sub(r"[^a-z0-9]+", "-", texto.lower().strip())
    return re.sub(r"-+", "-", texto).strip("-")


def carregar():
    """Devolve {secao: [peca, ...]} e o total de pecas."""
    IMG.mkdir(parents=True, exist_ok=True)
    for f in IMG.glob("*"):
        f.unlink()

    dados = json.loads(ENTRADA.read_text(encoding="utf-8"))
    vistos = {}

    for item in dados["items"]:
        if item.get("status") != "owned":
            continue
        bruto = item["name"].strip()
        if bruto in vistos:                     # peca repetida: conta junto
            vistos[bruto]["qtd"] += 1
            continue
        if bruto not in CURADORIA:
            print("  AVISO: peca sem curadoria ->", bruto)
            continue

        secao, nome, marca, papel = CURADORIA[bruto]
        arquivo = ""
        url = item.get("imageUrl") or ""
        if url.startswith("data:image/"):
            arquivo = f"{slug(nome)}.png"
            bruto_img = base64.b64decode(url.split(",", 1)[1])
            (IMG / arquivo).write_bytes(tirar_fundo(bruto_img))

        vistos[bruto] = {"secao": secao, "nome": nome, "marca": marca,
                         "papel": papel, "img": arquivo, "qtd": 1}

    secoes = {s: [] for s in SECOES}
    for peca in vistos.values():
        secoes[peca["secao"]].append(peca)
    total = sum(len(v) for v in secoes.values())
    return secoes, total


# ===========================================================
#  VISAO
# ===========================================================
def montar_css():
    cores = "\n".join(
        f'  --cor-{slug(s)}: {c};' for s, c in CORES.items()
    )
    return f"""
:root {{
  --fundo:      #070b12;
  --painel:     #0e1622;
  --slot:       #111b28;
  --linha:      #1e2a3a;
  --texto:      #f2efe6;
  --texto-fraco:#8d99ab;
  --ouro:       #efa02a;
  --verde:      #9bd45f;
{cores}
  --raio: 4px;
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  background: var(--fundo);
  color: var(--texto);
  font-family: "Space Grotesk", system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}}

h1, h2, h3, .slot-num, .painel-nome {{
  font-family: "Chakra Petch", system-ui, sans-serif;
  font-weight: 600;
}}

.quadro {{
  max-width: 1180px;
  margin: 0 auto;
  padding: 36px 24px 72px;
}}

/* ---------- cabeçalho: ficha do jogador ---------- */
.ficha {{
  display: flex;
  align-items: center;
  gap: 20px;
  padding-bottom: 22px;
  border-bottom: 1px solid var(--linha);
}}

.ficha img {{
  width: 76px; height: 76px;
  flex: none;
  filter: drop-shadow(0 6px 16px rgba(239,160,42,.25));
}}

.ficha h1 {{
  font-size: 30px;
  letter-spacing: -.5px;
  line-height: 1.1;
}}
.ficha h1 .c {{ color: var(--ouro); }}
.ficha h1 .s {{ color: var(--verde); }}

.ficha p {{
  margin-top: 2px;
  color: var(--texto-fraco);
  font-size: 15px;
}}

.ficha .horario {{
  margin-left: auto;
  text-align: right;
  color: var(--texto-fraco);
  font-size: 14px;
  line-height: 1.6;
}}
.ficha .horario b {{ color: var(--texto); font-weight: 500; }}

/* ---------- corpo: grade de slots + painel ---------- */
.corpo {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) 400px;
  gap: 40px;
  margin-top: 30px;
  align-items: start;
}}

.grupo + .grupo {{ margin-top: 26px; }}

.grupo h2 {{
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: .02em;
  margin-bottom: 10px;
  color: var(--cor);
}}
.grupo h2 span {{
  color: var(--texto-fraco);
  font-family: "Space Grotesk", sans-serif;
  font-size: 13px;
  font-weight: 400;
}}

.slots {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(86px, 1fr));
  gap: 8px;
}}

.slot {{
  position: relative;
  aspect-ratio: 1;
  border: 1px solid var(--linha);
  border-radius: var(--raio);
  background:
    radial-gradient(120% 120% at 50% 0%, rgba(255,255,255,.035), transparent 60%),
    var(--slot);
  padding: 9px;
  cursor: pointer;
  color: inherit;
  display: grid;
  place-items: center;
  transition: border-color .12s, background .12s;
  /* a entrada em sequencia acontece uma vez, no carregamento */
  opacity: 0;
  animation: entra .28s ease-out forwards;
  animation-delay: var(--atraso);
}}

.slot img {{
  width: 100%; height: 100%;
  object-fit: contain;
  pointer-events: none;
}}

.slot:hover,
.slot:focus-visible {{
  border-color: var(--cor);
  background: var(--slot);
  outline: none;
}}

.slot[aria-current="true"] {{
  border-color: var(--cor);
  box-shadow: 0 0 0 1px var(--cor), 0 0 18px -4px var(--cor);
}}

.slot .qtd {{
  position: absolute;
  right: 4px; bottom: 3px;
  font-family: "Chakra Petch", sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: var(--cor);
}}

@keyframes entra {{
  from {{ opacity: 0; transform: translateY(6px) scale(.96); }}
  to   {{ opacity: 1; transform: none; }}
}}

/* ---------- painel do item ---------- */
.painel {{
  position: sticky;
  top: 28px;
  border: 1px solid var(--linha);
  border-top: 2px solid var(--cor, var(--ouro));
  border-radius: var(--raio);
  background: var(--painel);
  padding: 22px;
}}

.painel-foto {{
  aspect-ratio: 4 / 3;
  display: grid;
  place-items: center;
  background:
    radial-gradient(90% 90% at 50% 25%, rgba(255,255,255,.05), transparent 70%);
  border-radius: var(--raio);
  margin-bottom: 18px;
}}
.painel-foto img {{
  max-width: 88%; max-height: 88%;
  object-fit: contain;
}}

.painel-marca {{
  font-size: 13px;
  letter-spacing: .06em;
  color: var(--cor, var(--ouro));
  min-height: 19px;
}}

.painel-nome {{
  font-size: 27px;
  line-height: 1.15;
  letter-spacing: -.4px;
  margin: 2px 0 10px;
}}

.painel-papel {{
  color: var(--texto-fraco);
  font-size: 15.5px;
  max-width: 46ch;
}}

.painel-rodape {{
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--linha);
  font-size: 13px;
  color: var(--texto-fraco);
}}

/* a troca de item e a unica animacao depois do carregamento,
   e ela responde ao que a pessoa faz */
.painel.trocando .painel-foto,
.painel.trocando .painel-texto {{
  opacity: 0;
  transform: translateY(4px);
}}
.painel-foto, .painel-texto {{
  transition: opacity .14s ease-out, transform .14s ease-out;
}}

/* ---------- rodapé ---------- */
.fim {{
  margin-top: 46px;
  padding-top: 22px;
  border-top: 1px solid var(--linha);
  display: flex;
  flex-wrap: wrap;
  gap: 10px 26px;
  align-items: baseline;
  font-size: 15px;
}}
.fim a {{
  color: var(--texto);
  text-decoration: none;
  border-bottom: 1px solid var(--ouro);
  padding-bottom: 1px;
}}
.fim a:hover, .fim a:focus-visible {{ color: var(--ouro); }}
.fim p {{ color: var(--texto-fraco); margin-left: auto; }}

/* ---------- telas pequenas ---------- */
@media (max-width: 880px) {{
  .corpo {{ grid-template-columns: 1fr; gap: 24px; }}
  .painel {{ position: static; order: -1; }}
  .ficha {{ flex-wrap: wrap; }}
  .ficha .horario {{ margin-left: 0; text-align: left; width: 100%; }}
  .slots {{ grid-template-columns: repeat(auto-fill, minmax(72px, 1fr)); }}
}}

@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; transition: none !important; }}
  .slot {{ opacity: 1; }}
}}
"""


def montar_html(secoes, total):
    e = html.escape
    grupos, dados_js, i = [], [], 0
    primeiro = None

    for secao in SECOES:
        pecas = secoes[secao]
        if not pecas:
            continue
        cor = CORES[secao]
        slots = []
        for peca in pecas:
            if primeiro is None:
                primeiro = i
            foto = (f'<img src="img/{peca["img"]}" alt="">' if peca["img"] else "")
            qtd = f'<span class="qtd">{peca["qtd"]}</span>' if peca["qtd"] > 1 else ""
            slots.append(
                f'<button class="slot" type="button" data-i="{i}" '
                f'style="--atraso:{i * 22}ms" '
                f'aria-label="{e(peca["nome"])}">{foto}{qtd}</button>'
            )
            dados_js.append({
                "nome": peca["nome"], "marca": peca["marca"], "papel": peca["papel"],
                "img": peca["img"], "cor": cor, "secao": secao, "qtd": peca["qtd"],
            })
            i += 1

        grupos.append(f"""    <section class="grupo" style="--cor:{cor}">
      <h2>{e(secao)} <span>{len(pecas)}</span></h2>
      <div class="slots">
{chr(10).join("        " + s for s in slots)}
      </div>
    </section>""")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inventário · thecoinsquash</title>
<meta name="description" content="As peças que fazem a live do thecoinsquash funcionar.">
<link rel="icon" href="img/favicon.png">
<meta property="og:title" content="Inventário · thecoinsquash">
<meta property="og:description" content="As peças que fazem a live funcionar.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=Space+Grotesk:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="estilo.css">
</head>
<body>
<div class="quadro">

  <header class="ficha">
    <img src="img/logo.png" alt="" width="76" height="76">
    <div>
      <h1>the<span class="c">coin</span><span class="s">squash</span></h1>
      <p>{total} peças em uso. Passe por uma delas para ver o que faz.</p>
    </div>
    <div class="horario">
      <b>Terça a sexta</b>, 21h30<br>
      <b>Sábado e domingo</b>, 16h
    </div>
  </header>

  <div class="corpo">
    <div class="colecao">
{chr(10).join(grupos)}
    </div>

    <aside class="painel" id="painel" aria-live="polite">
      <div class="painel-foto"><img id="p-img" src="" alt=""></div>
      <div class="painel-texto">
        <div class="painel-marca" id="p-marca"></div>
        <h3 class="painel-nome" id="p-nome"></h3>
        <p class="painel-papel" id="p-papel"></p>
        <div class="painel-rodape" id="p-rodape"></div>
      </div>
    </aside>
  </div>

  <footer class="fim">
    <a href="https://twitch.tv/thecoinsquash">Twitch</a>
    <a href="https://kick.com/thecoinsquash">Kick</a>
    <a href="https://instagram.com/cardoso.dego23">Instagram</a>
    <a href="https://x.com/thecoinsquash">X</a>
    <p>Sem valores, por opção: preço de hardware envelhece rápido.</p>
  </footer>
</div>

<script>
const PECAS = {json.dumps(dados_js, ensure_ascii=False)};
const painel = document.getElementById("painel");
const campos = {{
  img: document.getElementById("p-img"),
  marca: document.getElementById("p-marca"),
  nome: document.getElementById("p-nome"),
  papel: document.getElementById("p-papel"),
  rodape: document.getElementById("p-rodape"),
}};
const slots = [...document.querySelectorAll(".slot")];
let atual = -1;

function mostrar(i, fixar) {{
  if (i === atual) return;
  atual = i;
  const p = PECAS[i];
  painel.classList.add("trocando");
  window.setTimeout(() => {{
    painel.style.setProperty("--cor", p.cor);
    campos.img.src = p.img ? "img/" + p.img : "";
    campos.img.alt = p.nome;
    campos.marca.textContent = p.marca;
    campos.nome.textContent = p.nome;
    campos.papel.textContent = p.papel;
    campos.rodape.textContent = p.secao + (p.qtd > 1 ? " · " + p.qtd + " unidades" : "");
    painel.classList.remove("trocando");
  }}, 140);
  if (fixar) {{
    slots.forEach(s => s.removeAttribute("aria-current"));
    slots[i].setAttribute("aria-current", "true");
  }}
}}

slots.forEach((slot, i) => {{
  slot.addEventListener("mouseenter", () => mostrar(i, true));
  slot.addEventListener("focus", () => mostrar(i, true));
  slot.addEventListener("click", () => mostrar(i, true));
}});

mostrar({primeiro or 0}, true);
</script>
</body>
</html>
"""


# ===========================================================
#  CONTROLE
# ===========================================================
def main():
    secoes, total = carregar()
    for s in SECOES:
        print(f"  {s:12s} {len(secoes[s])}")
    print("  total:", total)

    shutil.copy(LOGO, IMG / "logo.png")
    shutil.copy(LOGO, IMG / "favicon.png")

    (SAIDA / "index.html").write_text(montar_html(secoes, total), encoding="utf-8")
    (SAIDA / "estilo.css").write_text(montar_css().strip() + "\n", encoding="utf-8")
    print("  site gravado em", SAIDA)


if __name__ == "__main__":
    main()
