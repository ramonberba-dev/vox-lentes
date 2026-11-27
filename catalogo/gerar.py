"""Gera catalogo/produtos.json lendo as páginas públicas da usevox.com.br (sem senha nem chave).
Roda no GitHub Actions a cada 30 min. As abas ficam em catalogo/abas.json (fácil de mexer)."""
import json, re, html, os, urllib.request, time
AQUI = os.path.dirname(os.path.abspath(__file__))
SITE = 'https://usevox.com.br'
UA = {'User-Agent': 'Mozilla/5.0 (catalogo VOX)'}

def baixar(url):
    for t in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read().decode('utf-8', 'replace')
        except Exception:
            time.sleep(3)
    return ''

def ler_categoria(caminho):
    itens, vistos = [], set()
    for pag in range(1, 30):
        s = baixar(f'{SITE}/{caminho.strip("/")}/page/{pag}/')
        blocos = re.split(r'(?=<div[^>]*js-item-product[^>]*data-product-id="\d+")', s)
        novos = 0
        for b in blocos[1:]:
            pid = re.search(r'data-product-id="(\d+)"', b).group(1)
            if pid in vistos: continue
            m = re.search(r'data-variants="([^"]*)"', b)
            if not m: continue
            vistos.add(pid); novos += 1
            var = json.loads(html.unescape(m.group(1)))
            url = re.search(r'href="(https://usevox\.com\.br/produtos/[^"]+)"', b)
            nome = re.search(r'(?:title|alt)="([^"]+)"', b)
            img = next((v.get('image_url') for v in var if v.get('image_url')), None)
            if not img:
                im = re.search(r'(?:data-srcset|srcset|src)="(//[^" ]+)', b); img = im.group(1) if im else None
            estoque = 0; inf = False
            for v in var:
                if v.get('available'):
                    st = v.get('stock')
                    if st is None: inf = True
                    else: estoque += int(st)
            p0 = min(var, key=lambda v: v.get('price_number') or 9e9)
            itens.append({
                'id': pid,
                'nome': html.unescape(nome.group(1)).strip() if nome else '',
                'url': url.group(1).split("?")[0] if url else '',
                'img': ('https:' + img) if img and img.startswith('//') else img,
                'preco': p0.get('price_number'),
                'de': p0.get('compare_at_price_number'),
                'estoque': 99 if inf else estoque,
                'tamanhos': sorted({str(v.get('option0') or '') for v in var if v.get('available') and (v.get('stock') is None or v.get('stock') > 0) and v.get('option0')}),
            })
        if novos == 0: break
    return itens

abas = json.load(open(os.path.join(AQUI, 'abas.json'), encoding='utf-8'))
saida = {'atualizado': time.strftime('%Y-%m-%dT%H:%M:%S-03:00', time.gmtime(time.time() - 3 * 3600)), 'abas': []}
for a in abas['abas']:
    lista = []
    for c in a['categorias']:
        for p in ler_categoria(c):
            if any(p['id'] == x['id'] for x in lista): continue
            if any(t.lower() in p['nome'].lower() for t in a.get('esconder_se_nome_tiver', [])): continue
            lista.append(p)
    saida['abas'].append({'id': a['id'], 'nome': a['nome'], 'itens': lista})
    print(a['nome'], len(lista))
json.dump(saida, open(os.path.join(AQUI, 'produtos.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
