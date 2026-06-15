# Markdown to Anki

**markdown-to-anki** is a lightweight Python CLI that automatically converts **raw Markdown files into Anki cards** using [AnkiConnect](https://foosoft.net/projects/anki-connect/). It's designed for learners and note-takers who prefer writing in Markdown and want to seamlessly sync their content into Anki.

## Installation

```shell
pip install markdown-to-anki
```

Requires Python 3.10+ and [AnkiConnect](https://foosoft.net/projects/anki-connect/) running in your Anki app.

## Getting Started

Open Anki, then run once to register note models and do the first import:

```shell
m2a --folder ~/notes/anki init all
```

From then on, use `anki sync` for day-to-day updates — it re-imports changed files and pushes everything to AnkiWeb:

```shell
m2a --folder ~/notes/anki anki sync
```

## Commands

| Command             | Description                                                                          |
| ------------------- | ------------------------------------------------------------------------------------ |
| `m2a init all`      | Register note models, import media and notes. Use for first-time setup.              |
| `m2a anki check`    | Verify the AnkiConnect server is reachable.                                          |
| `m2a anki init`     | Register note models only (no import).                                               |
| `m2a anki sync`     | Import media and notes, then trigger an AnkiWeb sync.                                |
| `m2a anki sync_web` | Trigger an AnkiWeb sync only (no re-import). Useful for cron.                        |

Only files modified within the last `TIME_RANGE` seconds (default 2 hours) are processed.

> **Force a full sync** — to re-sync all notes regardless of modification time, touch every Markdown file first:
> ```shell
> find ~/notes/anki -name "*.md" -exec touch {} +
> m2a --folder ~/notes/anki anki sync
> ```

## Configuration

Settings are resolved in this order — highest priority wins:

```
CLI flag  >  environment variable / .env  >  config file  >  default
```

### CLI flags

```shell
m2a --folder ~/notes/anki --url http://localhost:8765 anki sync
m2a --resources ~/my-templates init all
```

| Flag          | Description                                    | Default                 |
| ------------- | ---------------------------------------------- | ----------------------- |
| `--folder`    | Path to your Markdown notes dir                | see Config file         |
| `--url`       | AnkiConnect URL                                | `http://localhost:8765` |
| `--resources` | Path to custom card templates/styles directory | built-in resources      |

### Config file

Create `~/.config/markdown-to-anki/config.yaml` (respects `$XDG_CONFIG_HOME`):

```yaml
md_folder: ~/notes/anki
time_range: 7200
anki_url: http://localhost:8765
resources_dir: ~/notes/anki-templates
```

### Environment variables / `.env`

Place a `.env` file in the directory where you run `m2a`, or set the variables in your shell:

```dotenv
MD_FOLDER=~/notes/anki
TIME_RANGE=7200
ANKI_URL=http://localhost:8765
M2A_RESOURCES_DIR=~/notes/anki-templates
```

## Markdown Style

Each Markdown file may contain one or more cards. Use YAML frontmatter for per-file metadata and the comment separators below to split cards and fields:

```markdown
---
deck: M2A::Example::Math
tags: math, theorem
model: m2a-basic
# skip: 1   # uncomment to skip this file
---

<!--CARD-->

### Front of card 1

<!--FIELD-->

Back of card 1

<!--CARD-->
<!--TAGS: hard, exam-->

### Front of card 2

<!--FIELD-->

Back of card 2
```

Supported metadata keys: `deck`, `tags`, `model`, `skip`.

Per-card tags via `<!--TAGS: a, b-->` (anywhere inside a card section) are merged with the file-level `tags` from frontmatter.

### Built-in note types

| Model              | Fields                  | Description                          |
| ------------------ | ----------------------- | ------------------------------------ |
| `m2a-basic`        | Front, Back             | Simple front → back card             |
| `m2a-basic-reverse`| Front, Back             | Front → back and back → front        |
| `m2a-cloze`        | Text, Extra             | Cloze deletion card                  |
| `m2a-english`      | Word, Audio, Meaning    | Vocabulary card with audio support   |

### Cloze cards

Use Anki's native `{{c1::...}}` syntax in the `Text` field. Multiple deletions (`c1`, `c2`, …) are supported in a single card.

```markdown
---
deck: M2A::Example::Cloze
model: m2a-cloze
---

<!--CARD-->

The capital of {{c1::France}} is {{c2::Paris}}.

<!--FIELD-->

European geography.

<!--CARD-->

{{c1::Water}} boils at {{c2::100}}°C at standard pressure.

<!--FIELD-->

Basic chemistry fact.
```

The `Text` field holds the cloze content; `Extra` is shown on the back and can hold supplementary notes.

## Custom Resources

Point `--resources` (or `resources_dir` / `M2A_RESOURCES_DIR`) at your own directory to override built-in templates/styles and define new note types. Only the files you provide are overridden — everything else falls back to the built-in defaults.

### Override built-in templates or styles

Mirror the built-in layout under your resources directory:

```
my-resources/
└── anki/
    ├── styles/
    │   └── basic.css          # overrides the built-in basic.css
    └── templates/
        └── basic/
            └── front.html     # overrides the built-in front template
```

### Define custom note types

Place a YAML file per model inside a `models/` subdirectory:

```
my-resources/
├── models/
│   └── my-vocab.yaml
├── styles/
│   └── my-vocab.css
└── templates/
    └── my-vocab/
        ├── front.html
        └── back.html
```

**`models/my-vocab.yaml`**:

```yaml
name: my-vocab
fields:
  - Word
  - Definition
  - Example
is_cloze: false
css_file: styles/my-vocab.css      # relative to my-resources/
templates:
  - name: word-to-definition
    front_file: templates/my-vocab/front.html
    back_file: templates/my-vocab/back.html
```

Inline CSS and HTML are also supported instead of file references:

```yaml
name: my-simple
fields:
  - Question
  - Hint
  - Answer
css: ".card { font-family: sans-serif; }"
templates:
  - name: card
    front: "<div>{{Question}}</div><div class='hint'>{{Hint}}</div>"
    back: "<div>{{Answer}}</div>"
```

Fields map to `<!--FIELD-->` sections in order. A card with three fields uses two separators:

```markdown
---
model: my-vocab
deck: Languages::English
---

<!--CARD-->

hello

<!--FIELD-->

A common English greeting.

<!--FIELD-->

"Hello, how are you?" — used when meeting someone.
```

Run `m2a --resources my-resources/ init all` to register your models in Anki before syncing notes.

## Limitation

- DO NOT use dark theme in Anki — the rendered Markdown style does not support it.
- Attachments (images, audio) must be placed in the same directory as the Markdown file, or a subdirectory of it.

## Cronjob

Automatically sync your notes to AnkiWeb hourly:

```shell
crontab -e

# sync hourly (replace /usr/local/bin/m2a with the output of: which m2a)
5 * * * *  /usr/local/bin/m2a --folder ~/notes/anki anki sync_web &>/dev/null
```

## Examples

See the [example notes](https://github.com/rayyh/markdown-to-anki/tree/main/tests/fixtures) for working Markdown files covering basic cards, cloze deletions, math, code, and audio.

## License

This project is open-sourced and licensed under the [MIT license](https://github.com/rayyh/markdown-to-anki/blob/main/LICENSE).
