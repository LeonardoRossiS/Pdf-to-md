# Conversao de PDF para Markdown

O script `convert_pdfs.py` converte em lote os arquivos `.pdf` da pasta `pdfs`
para arquivos `.md` na pasta `mds`, mantendo o nome de cada arquivo.

## Preparacao

No PowerShell, na pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Conversao

```powershell
python convert_pdfs.py
```

Por padrao, arquivos `.md` que ja existem sao preservados. Para converte-los
novamente:

```powershell
python convert_pdfs.py --overwrite
```

As pastas padrao sao relativas ao projeto. Para usar outras pastas, informe
`--input-dir` e `--output-dir`.

## PDFs digitalizados (OCR opcional)

OCR e mais lento e so e necessario quando uma pagina nao possui texto
selecionavel. Instale o Tesseract e os dados de idioma para portugues e ingles,
depois execute:

```powershell
python convert_pdfs.py --ocr
```

O OCR e aplicado apenas a paginas com pouco texto selecionavel. Para escolher
outros idiomas do Tesseract, use `--ocr-language`, por exemplo
`--ocr-language eng`.

Revise o Markdown gerado, especialmente tabelas, colunas e paginas digitalizadas:
elementos complexos podem precisar de ajustes manuais.

## Limpar e dividir um Markdown por capitulos

O script `clean_split_markdown.py` preserva o arquivo original e cria os
capitulos em uma subpasta de `mds_limpos`. Ele remove apenas marcadores de
pagina no formato `**1d+ N**` e omite o material que vem antes do primeiro
capitulo indicado. O texto narrativo dentro dos capitulos e mantido: decidir
automaticamente se cada paragrafo e ou nao uma regra pode apagar explicacoes
importantes.

Para o `Manual do Aventureiro Alpha`, primeiro confira os titulos que o script
reconhecera, sem criar arquivos:

```powershell
python clean_split_markdown.py ".\mds\3dt-alpha-manual-do-aventureiro-alpha.md" `
  --chapter "Introducao=3D&T e TORMENTA. É difícil manter estes dois separados." `
  --chapter "Kits de Personagem=Kits de Personagem" `
  --dry-run
```

Se a verificacao listar os titulos esperados, rode o mesmo comando sem
`--dry-run`. Os arquivos serao salvos em
`mds_limpos\3dt-alpha-manual-do-aventureiro-alpha`, com um `index.md` e um
arquivo por capitulo. Informe os titulos Markdown exatos com `--chapter`,
repetindo a opcao na ordem em que os capitulos aparecem. Se os arquivos de
saida ja existirem, use `--overwrite` para substitui-los. Use `--book-title`
para corrigir o nome do manual quando o primeiro cabecalho nao for o titulo.

Cada processamento atualiza `mds_limpos\index.md`, o indice geral de todos os
manuais em `mds`. Os manuais cuja estrutura de capitulos nao foi extraida por
completo ou com confianca recebem um indice individual com link para o Markdown
original e uma nota para revisao manual da divisao.

O script nao classifica nem remove prosa por conteudo. Revise os arquivos
gerados para conferir tabelas, quebras de linha e possiveis marcadores de
pagina diferentes do padrao reconhecido.
