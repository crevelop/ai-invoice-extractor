"""Seeded vendor/product data and the invoice maker. All money is Decimal."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .models import InvoiceTruth, LineItem

CENT = Decimal("0.01")

BUYER = {
    "name": "Iberia Home Goods, S.L.",
    "tax_id": "ESB66412087",
    "address": "Carrer de Pallars 147, 3º 2ª",
    "city": "08018 Barcelona, España",
}


@dataclass(frozen=True)
class Vendor:
    name: str
    tax_id: str
    address: str
    city: str
    country: str
    number_fmt: str  # .format(year=..., seq=...)
    extra: dict[str, str] = field(default_factory=dict)


VENDORS: dict[str, Vendor] = {
    "es_clean": Vendor(
        "Cocinas del Ebro, S.L.", "ESB50823176", "Polígono Malpica, Calle E 24",
        "50016 Zaragoza, España", "ES", "F-{year}-{seq:04d}",
        {"iban": "ES91 2100 0418 4502 0005 1332", "email": "facturacion@cocinasdelebro.es"},
    ),
    "es_dense": Vendor(
        "Menaje Industrial Levante, S.A.", "ESA46228901", "Av. de la Cerámica 88",
        "46980 Paterna (Valencia), España", "ES", "{year}/{seq:05d}",
        {"iban": "ES76 0049 1500 0512 3456 7892", "phone": "+34 961 234 118"},
    ),
    "pt_reverse": Vendor(
        "Louças do Atlântico, Lda.", "PT509884217", "Rua das Indústrias 12, Armazém 4",
        "4470-605 Maia, Portugal", "PT", "FT {year}/{seq:03d}",
        {"iban": "PT50 0002 0123 1234 5678 9015 4", "email": "geral@loucasatlantico.pt"},
    ),
    "de_reverse": Vendor(
        "Küchenprofi Rheinland GmbH", "DE812940517", "Industriestraße 44",
        "50859 Köln, Deutschland", "DE", "RE-{year}-{seq:04d}",
        {"iban": "DE89 3704 0044 0532 0130 00", "hrb": "HRB 54021, Amtsgericht Köln"},
    ),
    "cn_export": Vendor(
        "Guangzhou Brightware Housewares Co., Ltd.", "91440101MA9W2XK37L",
        "No. 128 Huangpu East Road, Tianhe District",
        "Guangzhou 510700, China", "CN", "GBH-{year}{seq:04d}",
        {"bank": "Bank of China, Guangzhou Branch — SWIFT BKCHCNBJ400", "terms": "T/T 30 days, FOB Guangzhou"},
    ),
    "en_minimal": Vendor(
        "Brava Kitchen Supplies, S.L.", "ESB67443210", "Carrer de la Llacuna 22",
        "08005 Barcelona, Spain", "ES", "BKS-{seq:03d}",
        {"email": "billing@bravakitchen.com"},
    ),
    "es_multipage": Vendor(
        "Distribuciones Meridional, S.A.", "ESA28455301", "Ctra. de Andalucía km 12,4",
        "28906 Getafe (Madrid), España", "ES", "FA{year}-{seq:05d}",
        {"iban": "ES12 0081 0300 1100 0123 4567"},
    ),
    "es_handwritten": Vendor(
        "Ferretería y Menaje Soler, S.C.P.", "ESJ08773241", "Carrer Major 6",
        "17600 Figueres (Girona), España", "ES", "{seq:03d}/{year}",
        {"phone": "+34 972 501 233"},
    ),
}

PRODUCTS = {
    "es": [
        "Sartén antiadherente 24 cm", "Cazuela de acero inoxidable 5 L",
        "Juego de cuchillos cocina (6 pzas.)", "Tabla de corte bambú 40×30",
        "Olla a presión 6 L", "Escurridor plegable silicona",
        "Batería de cocina 8 piezas", "Fuente de horno cerámica 32 cm",
        "Molinillo de pimienta acero", "Vajilla porcelana 18 piezas",
        "Cafetera italiana 6 tazas", "Ensaladera cristal templado 26 cm",
    ],
    "pt": [
        "Frigideira cerâmica 28 cm", "Panela inox fundo triplo 4 L",
        "Conjunto de talheres 24 peças", "Travessa de forno em grés",
        "Jarro de vidro 1,5 L", "Tábua de corte em faia",
        "Serviço de café porcelana 12 pçs.", "Formas de silicone (6 un.)",
    ],
    "de": [
        "Edelstahl-Kochtopf 5 L", "Gusseisen-Bratpfanne 26 cm",
        "Messerblock Buche 7-teilig", "Schüsselset Glas (4 Stück)",
        "Auflaufform Keramik 34 cm", "Küchenwaage digital 5 kg",
        "Schneidebrett Bambus groß", "Salatschleuder Edelstahl",
    ],
    "en": [
        "Stainless steel mixing bowl set (5 pcs)", "Non-stick frying pan 28 cm",
        "Silicone utensil set (10 pcs)", "Glass food storage containers (8 pcs)",
        "Cast iron dutch oven 4.7 L", "Bamboo serving tray 45×30 cm",
        "Ceramic dinnerware set 16 pcs", "Kitchen scale digital 5 kg",
        "Double-wall glass tumblers (6 pcs)", "Stackable spice jars (12 pcs)",
    ],
}


def make_invoice(
    rng: random.Random,
    vendor: Vendor,
    seq: int,
    *,
    locale: str = "es",
    currency: str = "EUR",
    tax_rate: Decimal = Decimal("21"),
    reverse_charge: bool = False,
    n_items: tuple[int, int] = (3, 7),
    with_due_date: bool = True,
    year: int = 2026,
) -> InvoiceTruth:
    """Build one internally-consistent invoice (see gen/__init__.py: no lying docs)."""
    issue = date(year, rng.randint(1, 6), rng.randint(1, 28))
    due = issue + timedelta(days=rng.choice([15, 30, 45, 60])) if with_due_date else None

    pool = PRODUCTS[locale]
    k = rng.randint(*n_items)
    if k <= len(pool):
        descs = rng.sample(pool, k=k)
    else:  # multi-page invoices need more rows than the pool: add catalogue refs
        descs = [f"{pool[i % len(pool)]} — ref. {1000 + i}" for i in range(k)]
    items = []
    for desc in descs:
        qty = Decimal(rng.choice([1, 2, 4, 6, 10, 12, 24, 48]))
        unit = (Decimal(rng.randint(180, 9500)) / 100).quantize(CENT)
        items.append(LineItem(description=desc, quantity=qty, unit_price=unit,
                              total=(qty * unit).quantize(CENT)))

    subtotal = sum((li.total for li in items), Decimal("0"))
    rate = Decimal("0") if reverse_charge else tax_rate
    tax = (subtotal * rate / 100).quantize(CENT, rounding=ROUND_HALF_UP)

    return InvoiceTruth(
        vendor_name=vendor.name,
        vendor_tax_id=vendor.tax_id,
        invoice_number=vendor.number_fmt.format(year=year, seq=seq),
        issue_date=issue,
        due_date=due,
        currency=currency,
        line_items=items,
        subtotal=subtotal,
        tax_rate=rate,
        tax_amount=tax,
        total=subtotal + tax,
        reverse_charge=reverse_charge,
    )
