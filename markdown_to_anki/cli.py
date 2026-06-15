import click

from markdown_to_anki import __version__
from markdown_to_anki.config import ANKI_BASE_URL
from markdown_to_anki.services.anki import ensure_models, import_medias, import_notes
from markdown_to_anki.services.anki_api import AnkiApi


def _ctx_get(ctx, key):
    return ctx.obj.get(key) if ctx.obj else None


def _make_api(anki_url: str | None) -> AnkiApi:
    return AnkiApi(anki_uri=anki_url or ANKI_BASE_URL)


@click.group()
@click.version_option(
    __version__, "-V", "--version", message="m2a %(version)s"
)
@click.option(
    "--folder",
    default=None,
    help="Path to markdown notes directory (overrides MD_FOLDER env / config file).",
)
@click.option(
    "--url",
    default=None,
    help="AnkiConnect URL (overrides ANKI_URL env / config file).",
)
@click.option(
    "--resources",
    default=None,
    help="Path to custom resources directory for card templates and styles.",
)
@click.pass_context
def cli(ctx, folder, url, resources):
    from markdown_to_anki import config as m2a_config
    from markdown_to_anki.helpers.path import set_resources_dir

    ctx.ensure_object(dict)
    if folder:
        ctx.obj["MD_FOLDER"] = folder
    if url:
        ctx.obj["ANKI_URL"] = url
    set_resources_dir(resources or m2a_config.RESOURCES_DIR)


@cli.command("version")
def version():
    """Print the m2a version."""
    click.echo(__version__)


@cli.command("check")
@click.pass_context
def check(ctx):
    """Verify the AnkiConnect server is reachable."""
    try:
        _make_api(_ctx_get(ctx, "ANKI_URL")).version()
    except Exception:
        click.secho("Connection Refused", fg="red")
        return
    click.secho("Connection OK!", fg="green")


@cli.command("init")
@click.pass_context
def init(ctx):
    """Register note models in Anki. Run once before your first sync."""
    click.echo(ensure_models(anki_url=_ctx_get(ctx, "ANKI_URL")))
    click.echo("done.")


@cli.command("sync")
@click.pass_context
def sync(ctx):
    """Import media and notes, then trigger an AnkiWeb sync."""
    md_folder = _ctx_get(ctx, "MD_FOLDER")
    anki_url = _ctx_get(ctx, "ANKI_URL")
    click.echo("import medias")
    click.echo(import_medias(md_folder=md_folder, anki_url=anki_url))
    click.echo("import notes")
    click.echo(import_notes(md_folder=md_folder, anki_url=anki_url))
    try:
        click.echo(_make_api(anki_url).sync())
    except Exception:
        click.secho("Connection Refused", fg="red")


@cli.command("sync_web")
@click.pass_context
def sync_web(ctx):
    """Trigger an AnkiWeb sync only (no re-import). Useful for cron."""
    try:
        click.echo(_make_api(_ctx_get(ctx, "ANKI_URL")).sync())
    except Exception:
        click.secho("Connection Refused", fg="red")
        return
    click.secho("Sync OK!", fg="green")


if __name__ == "__main__":
    cli()
