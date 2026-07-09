from daily.adapters.misc import EchoSummarizer


def test_echo_summarizer_usa_titulo_quando_disponivel():
    summary = EchoSummarizer().summarize("conteudo relevante", {"title": "Documento"})

    assert summary == "Resumo de 'Documento': conteudo relevante"


def test_echo_summarizer_trunca_texto_longo():
    text = "a" * 400

    summary = EchoSummarizer().summarize(text, {})

    assert summary.startswith("Resumo: ")
    assert summary.endswith("…")
    assert len(summary) == len("Resumo: ") + 280 + 1
