# Traductions des pages villes — OnBouge

Les pages de communes d'[OnBouge](https://onbouge.eu) s'affichent dans la langue du pays. Ce dépôt traduit leurs
textes (déjà publics sur le site) avec des **modèles libres**, sur les machines de GitHub Actions : aucune API, aucun coût.

- `lots/<langue>.jsonl` : textes à traduire, poussés par le serveur OnBouge.
- `traduire.py` : la traduction (une machine par langue).
- Releases `trad-AAAAMMJJ-HHMM` : `<langue>.jsonl` + `SHA256SUMS`, téléchargés par le serveur.

## Modèles (merci à Helsinki-NLP / OPUS-MT, Université d'Helsinki)

| Langue | Modèle | Licence |
|---|---|---|
| italien | [opus-mt-tc-big-itc-itc](https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-itc-itc) | CC-BY 4.0 |
| espagnol | [opus-mt-fr-es](https://huggingface.co/Helsinki-NLP/opus-mt-fr-es) | Apache 2.0 |
| allemand | [opus-mt-fr-de](https://huggingface.co/Helsinki-NLP/opus-mt-fr-de) | Apache 2.0 |
| anglais | [opus-mt-tc-big-fr-en](https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-fr-en) | CC-BY 4.0 |
| néerlandais | fr→en puis [opus-mt-en-nl](https://huggingface.co/Helsinki-NLP/opus-mt-en-nl) | CC-BY 4.0 / Apache 2.0 |

Tiedemann J. & Thottingal S. (2020), *OPUS-MT — Building open translation services for the World*, EAMT.
