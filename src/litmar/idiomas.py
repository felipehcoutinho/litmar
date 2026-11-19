"""Idiomas admitidos por la interfaz y las revisiones."""

from __future__ import annotations

from typing import Literal

Idioma = Literal["es", "pt-BR", "en", "ja"]

INSTRUCCIONES: dict[Idioma, str] = {
    "es": "Responde exclusivamente en español.",
    "pt-BR": "Responda exclusivamente em português do Brasil.",
    "en": "Respond exclusively in English.",
    "ja": "日本語のみで回答してください。",
}

TEXTOS: dict[Idioma, dict[str, str]] = {
    "es": {
        "no_articulos": "No se encontraron artículos con resumen para esta pregunta.",
        "busquedas": "Búsquedas",
        "referencias": "Referencias",
        "avisos": "Avisos",
        "no_verificada": "cita no verificada",
        "sin_informe_agente": "El agente no escribió ningún informe.",
        "limite_agente": "El agente alcanzó el límite de {max_pasos} pasos sin terminar.",
        "hasta_donde": "Hasta dónde llegó",
        "agente_detencion": "El agente se detuvo al alcanzar el límite de pasos.",
        "doi_no_busqueda": "El informe citaba DOI que no salieron de ninguna búsqueda",
        "marca_no_verificada": "marcados como «{marca}».",
    },
    "pt-BR": {
        "no_articulos": "Não foram encontrados artigos com resumo para esta pergunta.",
        "busquedas": "Buscas",
        "referencias": "Referências",
        "avisos": "Avisos",
        "no_verificada": "citação não verificada",
        "sin_informe_agente": "O agente não escreveu um relatório.",
        "limite_agente": "O agente atingiu o limite de {max_pasos} etapas sem terminar.",
        "hasta_donde": "Até onde chegou",
        "agente_detencion": "O agente parou ao atingir o limite de etapas.",
        "doi_no_busqueda": "O relatório citava DOIs que não vieram de nenhuma busca",
        "marca_no_verificada": "marcados como «{marca}».",
    },
    "en": {
        "no_articulos": "No articles with abstracts were found for this question.",
        "busquedas": "Searches",
        "referencias": "References",
        "avisos": "Warnings",
        "no_verificada": "unverified citation",
        "sin_informe_agente": "The agent did not write a report.",
        "limite_agente": "The agent reached the limit of {max_pasos} steps before finishing.",
        "hasta_donde": "Progress so far",
        "agente_detencion": "The agent stopped after reaching the step limit.",
        "doi_no_busqueda": "The report cited DOIs that were not returned by any search",
        "marca_no_verificada": "marked as “{marca}”.",
    },
    "ja": {
        "no_articulos": "この質問に関連する要約付き論文は見つかりませんでした。",
        "busquedas": "検索語",
        "referencias": "参考文献",
        "avisos": "注意事項",
        "no_verificada": "未確認の引用",
        "sin_informe_agente": "エージェントはレポートを作成しませんでした。",
        "limite_agente": "エージェントは完了前に{max_pasos}ステップの上限に達しました。",
        "hasta_donde": "進捗状況",
        "agente_detencion": "エージェントはステップ上限に達して停止しました。",
        "doi_no_busqueda": "レポートには検索結果にないDOIが含まれていました",
        "marca_no_verificada": "「{marca}」として表示しました。",
    },
}


def texto(idioma: Idioma, clave: str) -> str:
    return TEXTOS[idioma][clave]
