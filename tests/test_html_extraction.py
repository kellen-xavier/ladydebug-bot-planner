from daily.adapters.misc import extract_text_from_html


def test_extract_text_from_html_remove_tags_e_pega_titulo():
    html = """
    <!DOCTYPE html><html lang="en"><head><meta charSet="utf-8"/>
    <title>apps-on-teams</title>
    <style>.hidden { display: none; }</style>
    </head>
    <body>
      <script>console.log('nao deve aparecer');</script>
      <h1>Apps on Teams</h1>
      <p>Documentacao para melhorias futuras do bot no servidor.</p>
    </body></html>
    """
    title, text = extract_text_from_html(html)

    assert title == "apps-on-teams"
    assert "<" not in text
    assert ">" not in text
    assert "console.log" not in text
    assert "display: none" not in text
    assert "Documentacao para melhorias futuras do bot no servidor." in text


def test_extract_text_from_html_sem_title_retorna_vazio():
    title, text = extract_text_from_html("<html><body><p>sem titulo aqui</p></body></html>")
    assert title == ""
    assert "sem titulo aqui" in text


def test_extract_text_from_html_decodifica_entidades():
    _, text = extract_text_from_html("<p>Caf&eacute; &amp; ch&aacute;</p>")
    assert "Café & chá" in text
