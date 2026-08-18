#!/usr/bin/env python3

import argparse
import json
import os
import time
from pathlib import Path

import requests


# ============================================================
# CONFIGURAÇÃO
# ============================================================

GRAPH_API_VERSION = "v26.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

PAGE_ID = "1296658466864025"

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

DEFAULT_JSON = REPO_ROOT / "data" / "products.json"
DEFAULT_POSTED_LOG = REPO_ROOT / "data" / "posted_log.json"

DEFAULT_SITE_URL = "https://tabaratao.com.br/"


# ============================================================
# ARQUIVOS
# ============================================================

def load_products(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {path}"
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(
            "products.json precisa conter uma lista JSON."
        )

    return data


def load_posted_log(path: Path) -> set:
    if not path.exists():
        return set()

    try:
        with path.open("r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_posted_log(path: Path, posted_ids: set):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(
            sorted(posted_ids),
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# FORMATAÇÃO
# ============================================================

def format_brl(value):
    if not isinstance(value, (int, float)):
        return "Confira o preço atual"

    return (
        f"R$ {value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def make_post_text(product: dict, site_url: str) -> str:
    title = product.get("title") or "Oferta encontrada"
    price = format_brl(product.get("price"))
    affiliate = product.get("affiliateLink") or ""

    return (
        "🔥 OFERTA DO DIA\n\n"
        f"🛍️ {title}\n"
        f"💰 {price}\n\n"
        "👉 Comprar na Amazon:\n"
        f"{affiliate}\n\n"
        "🔎 Ver no Tabaratão:\n"
        f"{site_url}\n\n"
        "#publicidade #afiliado #ofertas #tabaratao"
    )


# ============================================================
# IMAGEM
# ============================================================

def resolve_image_path(product: dict, json_path: Path):
    image_field = product.get("image")

    if not image_field:
        return None

    candidate_bases = [
        json_path.parent,
        json_path.parent.parent,
        REPO_ROOT,
    ]

    for base in candidate_bases:
        candidate = (base / image_field).resolve()

        if candidate.exists():
            return candidate

    return None


def build_public_image_url(product: dict, site_url: str):
    image_field = product.get("image")

    if not image_field:
        return None

    if (
        image_field.startswith("http://")
        or image_field.startswith("https://")
    ):
        return image_field

    return (
        site_url.rstrip("/")
        + "/"
        + image_field.lstrip("/")
    )


# ============================================================
# FACEBOOK API
# ============================================================

def parse_response(response):
    try:
        body = response.json()
    except Exception:
        body = response.text

    return body


def handle_response(response):
    body = parse_response(response)

    if not response.ok:
        raise RuntimeError(
            f"Facebook API HTTP {response.status_code}: {body}"
        )

    return body


def validate_page_token(page_token: str, page_id: str):
    """
    Valida que o token configurado é realmente um Page Access Token
    da Página esperada.
    """
    url = f"{GRAPH_BASE}/me"
    response = requests.get(
        url,
        params={
            "access_token": page_token,
            "fields": "id,name",
        },
        timeout=30,
    )

    body = handle_response(response)

    if body.get("id") != page_id:
        raise RuntimeError(
            "O token informado não corresponde à Página configurada. "
            f"Esperado: {page_id}; recebido: {body.get('id')}"
        )

    print(
        f"Token validado para a Página: "
        f"{body.get('name')} (ID {body.get('id')})"
    )


def publish_text_only(
    message: str,
    page_id: str,
    page_token: str
):
    url = f"{GRAPH_BASE}/{page_id}/feed"

    response = requests.post(
        url,
        data={
            "message": message,
            "access_token": page_token,
        },
        timeout=30,
    )

    return handle_response(response)


def publish_with_photo(
    message: str,
    image_url: str,
    page_id: str,
    page_token: str
):
    """
    Publica foto usando URL pública.
    Não faz upload do arquivo local.
    """

    url = f"{GRAPH_BASE}/{page_id}/photos"

    response = requests.post(
        url,
        data={
            "caption": message,
            "url": image_url,
            "access_token": page_token,
        },
        timeout=60,
    )

    return handle_response(response)


# ============================================================
# SELEÇÃO DE PRODUTO
# ============================================================

def pick_product_index(
    products,
    posted_ids,
    explicit_index
):
    if explicit_index is not None:

        if explicit_index < 0 or explicit_index >= len(products):
            raise IndexError(
                f"Índice {explicit_index} fora do intervalo "
                f"0..{len(products) - 1}."
            )

        return explicit_index

    for index, product in enumerate(products):

        product_id = (
            product.get("id")
            or product.get("asin")
        )

        if product_id not in posted_ids:
            return index

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Publica uma oferta do products.json "
            "na Página do Facebook."
        )
    )

    parser.add_argument(
        "--json",
        default=str(DEFAULT_JSON),
        help="Caminho para o products.json."
    )

    parser.add_argument(
        "--page-id",
        default=os.getenv(
            "META_PAGE_ID",
            PAGE_ID
        ),
        help="ID da Página do Facebook."
    )

    parser.add_argument(
        "--index",
        type=int,
        default=None,
        help=(
            "Índice do produto a publicar. "
            "Se omitido, escolhe o primeiro ainda não publicado."
        )
    )

    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help=(
            "Quantidade de produtos a publicar. "
            "Seleciona automaticamente produtos ainda não publicados."
        ),
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Intervalo em segundos entre publicações quando --count é usado.",
    )

    parser.add_argument(
        "--posted-log",
        default=str(DEFAULT_POSTED_LOG),
        help="Arquivo de produtos já publicados."
    )

    parser.add_argument(
        "--site-url",
        default=DEFAULT_SITE_URL,
        help="URL pública do site."
    )

    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Publica somente texto."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Testa leitura, seleção e URL da imagem "
            "sem publicar no Facebook."
        )
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # TOKEN
    # --------------------------------------------------------

    page_token = os.getenv(
        "META_PAGE_ACCESS_TOKEN"
    )

    if not page_token and not args.dry_run:
        raise RuntimeError(
            "META_PAGE_ACCESS_TOKEN não está definido."
        )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    json_path = Path(args.json)
    posted_log_path = Path(args.posted_log)

    products = load_products(
        json_path
    )

    if not products:
        raise RuntimeError(
            "products.json está vazio."
        )

    posted_ids = load_posted_log(
        posted_log_path
    )

    if args.index is not None and args.count is not None:
        raise ValueError("Use --index OU --count, não os dois.")

    if args.count is not None and args.count <= 0:
        raise ValueError("--count precisa ser maior que zero.")

    if args.interval < 0:
        raise ValueError("--interval não pode ser negativo.")

    # --------------------------------------------------------
    # SELEÇÃO DA FILA
    # --------------------------------------------------------

    if args.index is not None:
        indices = [args.index]
    else:
        desired = args.count if args.count is not None else 1
        indices = []

        for candidate_index, candidate in enumerate(products):
            candidate_id = (
                candidate.get("id")
                or candidate.get("asin")
                or f"index-{candidate_index}"
            )

            if candidate_id not in posted_ids:
                indices.append(candidate_index)

            if len(indices) >= desired:
                break

    if not indices:
        print("Nenhum produto disponível para publicação.")
        return

    if args.dry_run:
        print()
        print("=" * 60)
        print("DRY-RUN")
        print("=" * 60)
        print(f"Produtos selecionados: {len(indices)}")

        for order, index in enumerate(indices, start=1):
            product = products[index]
            image_path = None
            image_url = None

            if not args.text_only:
                image_path = resolve_image_path(product, json_path)
                image_url = build_public_image_url(
                    product,
                    args.site_url
                )

            print()
            print(f"[{order}/{len(indices)}] índice={index}")
            print(f"Produto: {product.get('title', '(sem título)')}")
            print(f"ASIN: {product.get('asin', '(sem ASIN)')}")
            print(
                "Imagem pública: "
                f"{image_url if image_url else '(não disponível)'}"
            )

        print()
        print("DRY-RUN: nenhuma publicação foi enviada.")
        return

    # --------------------------------------------------------
    # VALIDA PAGE ACCESS TOKEN DIRETO
    # --------------------------------------------------------

    validate_page_token(
        page_token,
        args.page_id
    )

    # --------------------------------------------------------
    # LOOP DE PUBLICAÇÃO
    # --------------------------------------------------------

    success_count = 0
    error_count = 0

    for order, index in enumerate(indices, start=1):

        product = products[index]

        product_id = (
            product.get("id")
            or product.get("asin")
            or f"index-{index}"
        )

        message = make_post_text(
            product,
            args.site_url
        )

        image_path = None
        image_url = None

        if not args.text_only:
            image_path = resolve_image_path(
                product,
                json_path
            )

            image_url = build_public_image_url(
                product,
                args.site_url
            )

        print()
        print("=" * 60)
        print(f"PUBLICAÇÃO {order}/{len(indices)}")
        print("=" * 60)
        print(f"Índice:         {index}")
        print(f"Produto:        {product.get('title', '(sem título)')}")
        print(f"ASIN:           {product.get('asin', '(sem ASIN)')}")
        print(
            "Imagem local:   "
            f"{image_path if image_path else '(não encontrada)'}"
        )
        print(
            "Imagem pública: "
            f"{image_url if image_url else '(não disponível)'}"
        )

        try:
            if image_url:
                print("Publicando como foto usando URL pública...")

                result = publish_with_photo(
                    message,
                    image_url,
                    args.page_id,
                    page_token
                )
            else:
                print(
                    "Sem imagem pública. "
                    "Publicando somente texto..."
                )

                result = publish_text_only(
                    message,
                    args.page_id,
                    page_token
                )

            print()
            print("PUBLICAÇÃO REALIZADA COM SUCESSO")
            print(result)

            posted_ids.add(product_id)

            save_posted_log(
                posted_log_path,
                posted_ids
            )

            success_count += 1

        except Exception as error:
            error_count += 1
            print(f"ERRO AO PUBLICAR {product_id}: {error}")

        if (
            args.count is not None
            and order < len(indices)
            and args.interval > 0
        ):
            print(
                f"Aguardando {args.interval} segundos "
                "antes da próxima publicação..."
            )
            time.sleep(args.interval)

    print()
    print("=" * 60)
    print("RESUMO")
    print("=" * 60)
    print(f"Solicitados: {len(indices)}")
    print(f"Publicados:  {success_count}")
    print(f"Com erro:    {error_count}")
    print(f"Posted log:  {posted_log_path}")


if __name__ == "__main__":
    main()
